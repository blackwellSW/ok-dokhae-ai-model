"""
Gemma 3 파인튜닝 모듈
LoRA 기반 효율적 학습
"""

import os
import json
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass, field

import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling,
    BitsAndBytesConfig
)
from peft import (
    LoraConfig,
    get_peft_model,
    prepare_model_for_kbit_training,
    TaskType
)
from datasets import load_dataset, Dataset


@dataclass
class TrainingConfig:
    """학습 설정 데이터 클래스"""
    # Model
    model_name: str = "google/gemma-3-9b-it"
    load_in_4bit: bool = True
    torch_dtype: str = "bfloat16"

    # LoRA
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    target_modules: List[str] = field(
        default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj"]
    )

    # Training
    output_dir: str = "models/gemma_finetuned"
    num_train_epochs: int = 3
    per_device_train_batch_size: int = 4
    gradient_accumulation_steps: int = 4
    learning_rate: float = 2e-4
    max_length: int = 1024
    warmup_steps: int = 100
    logging_steps: int = 10
    save_steps: int = 100

    # Data paths (TODO: 실제 경로로 변경)
    train_data_path: str = ""  # TODO: 학습 데이터 경로
    valid_data_path: str = ""  # TODO: 검증 데이터 경로


class GemmaTrainer:
    """Gemma 3 파인튜닝 클래스"""

    def __init__(self, config: Optional[TrainingConfig] = None):
        """
        Args:
            config: 학습 설정 (None이면 기본값 사용)
        """
        self.config = config or TrainingConfig()
        self.model = None
        self.tokenizer = None

        # LoRA 설정
        self.lora_config = LoraConfig(
            r=self.config.lora_r,
            lora_alpha=self.config.lora_alpha,
            target_modules=self.config.target_modules,
            lora_dropout=self.config.lora_dropout,
            bias="none",
            task_type=TaskType.CAUSAL_LM
        )

    def load_model(self) -> tuple:
        """
        4-bit 양자화 모델 로드

        Returns:
            tuple: (model, tokenizer)
        """
        print(f"📦 모델 로딩: {self.config.model_name}")

        # Tokenizer 로드
        tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            trust_remote_code=True
        )
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.padding_side = "right"

        # 4-bit 양자화 설정
        if self.config.load_in_4bit:
            bnb_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=getattr(torch, self.config.torch_dtype),
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4"
            )
        else:
            bnb_config = None

        # 모델 로드
        model = AutoModelForCausalLM.from_pretrained(
            self.config.model_name,
            quantization_config=bnb_config,
            device_map="auto",
            torch_dtype=getattr(torch, self.config.torch_dtype),
            trust_remote_code=True
        )

        # LoRA를 위한 모델 준비
        if self.config.load_in_4bit:
            model = prepare_model_for_kbit_training(model)

        # LoRA 적용
        model = get_peft_model(model, self.lora_config)

        # 학습 가능한 파라미터 출력
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in model.parameters())
        print(f"학습 가능 파라미터: {trainable_params:,} / {total_params:,} ({100 * trainable_params / total_params:.2f}%)")

        self.model = model
        self.tokenizer = tokenizer

        return model, tokenizer

    def prepare_dataset(self, data_path: str) -> Dataset:
        """
        데이터셋 준비

        Args:
            data_path: JSONL 데이터 파일 경로

        Returns:
            Dataset: 토큰화된 데이터셋
        """
        if not data_path or not Path(data_path).exists():
            print(f"⚠️ 데이터 파일을 찾을 수 없습니다: {data_path}")
            print("   학습 데이터 경로를 설정해주세요.")
            return None

        # 데이터 로드
        dataset = load_dataset('json', data_files=data_path, split='train')

        def format_and_tokenize(example):
            """데이터 포맷팅 및 토큰화"""
            # 학습 텍스트 구성
            if all(k in example for k in ("instruction", "input", "output")):
                instruction = str(example.get("instruction", ""))
                user_input = str(example.get("input", ""))
                output = str(example.get("output", ""))
            else:
                # raw 형식(id/source/passage/question/answer)도 학습 가능하게 지원
                instruction = "학생의 사고를 유도하며 작품을 해설하세요."
                passage = str(example.get("passage", ""))
                question = str(example.get("question", ""))
                answer = str(example.get("answer", ""))
                user_input = f"[지문]\n{passage}\n\n[질문]\n{question}"
                output = answer

            text = f"""{instruction}

{user_input}

{output}"""

            # 토큰화
            tokens = self.tokenizer(
                text,
                truncation=True,
                max_length=self.config.max_length,
                padding="max_length"
            )
            tokens["labels"] = tokens["input_ids"].copy()

            return tokens

        # 토큰화 적용
        tokenized_dataset = dataset.map(
            format_and_tokenize,
            remove_columns=dataset.column_names
        )

        print(f"✅ 데이터셋 준비 완료: {len(tokenized_dataset)}개")
        return tokenized_dataset

    def train(
        self,
        train_dataset: Optional[Dataset] = None,
        eval_dataset: Optional[Dataset] = None,
        resume_from_checkpoint: Optional[str] = None
    ) -> str:
        """
        학습 실행

        Args:
            train_dataset: 학습 데이터셋 (None이면 config 경로에서 로드)
            eval_dataset: 평가 데이터셋 (선택)
            resume_from_checkpoint: 체크포인트에서 재시작

        Returns:
            str: 저장된 모델 경로
        """
        # 모델 로드
        if self.model is None:
            self.load_model()

        # 데이터셋 준비
        if train_dataset is None:
            if not self.config.train_data_path:
                print("⚠️ 학습 데이터 경로가 설정되지 않았습니다.")
                print("   config.train_data_path를 설정해주세요.")
                return None
            train_dataset = self.prepare_dataset(self.config.train_data_path)

        if train_dataset is None:
            print("❌ 학습 데이터가 없습니다.")
            return None

        if eval_dataset is None and self.config.valid_data_path:
            eval_dataset = self.prepare_dataset(self.config.valid_data_path)

        # 학습 인자 설정
        training_args = TrainingArguments(
            output_dir=self.config.output_dir,
            num_train_epochs=self.config.num_train_epochs,
            per_device_train_batch_size=self.config.per_device_train_batch_size,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            learning_rate=self.config.learning_rate,
            fp16=True,
            logging_steps=self.config.logging_steps,
            save_steps=self.config.save_steps,
            warmup_steps=self.config.warmup_steps,
            optim="paged_adamw_8bit",
            save_total_limit=3,
            report_to="none",  # wandb 등 비활성화
            evaluation_strategy="steps" if eval_dataset else "no",
            eval_steps=self.config.save_steps if eval_dataset else None,
        )

        # Data Collator
        data_collator = DataCollatorForLanguageModeling(
            tokenizer=self.tokenizer,
            mlm=False
        )

        # Trainer 생성
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            data_collator=data_collator
        )

        print("=" * 60)
        print("🚀 학습 시작")
        print("=" * 60)
        print(f"   모델: {self.config.model_name}")
        print(f"   데이터: {len(train_dataset)}개")
        print(f"   Epochs: {self.config.num_train_epochs}")
        print(f"   Batch size: {self.config.per_device_train_batch_size}")
        print(f"   Learning rate: {self.config.learning_rate}")
        print("=" * 60)

        # 학습 실행
        trainer.train(resume_from_checkpoint=resume_from_checkpoint)

        # 모델 저장
        output_path = Path(self.config.output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        trainer.save_model(str(output_path))
        self.tokenizer.save_pretrained(str(output_path))

        # 설정 저장
        config_path = output_path / "training_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config.__dict__, f, ensure_ascii=False, indent=2)

        print("=" * 60)
        print(f"✅ 학습 완료! 모델 저장: {output_path}")
        print("=" * 60)

        return str(output_path)

    @classmethod
    def from_yaml(cls, config_path: str) -> "GemmaTrainer":
        """
        YAML 설정 파일에서 Trainer 생성

        Args:
            config_path: YAML 설정 파일 경로

        Returns:
            GemmaTrainer: 설정이 적용된 Trainer
        """
        import yaml

        with open(config_path, 'r', encoding='utf-8') as f:
            yaml_config = yaml.safe_load(f)

        config = TrainingConfig(
            # Model settings
            model_name=yaml_config.get('model', {}).get('name', TrainingConfig.model_name),
            load_in_4bit=yaml_config.get('model', {}).get('load_in_4bit', True),
            torch_dtype=yaml_config.get('model', {}).get('torch_dtype', 'bfloat16'),

            # LoRA settings
            lora_r=yaml_config.get('lora', {}).get('r', 16),
            lora_alpha=yaml_config.get('lora', {}).get('lora_alpha', 32),
            lora_dropout=yaml_config.get('lora', {}).get('lora_dropout', 0.05),
            target_modules=yaml_config.get('lora', {}).get('target_modules', ["q_proj", "k_proj", "v_proj", "o_proj"]),

            # Training settings
            output_dir=yaml_config.get('training', {}).get('output_dir', 'models/gemma_finetuned'),
            num_train_epochs=yaml_config.get('training', {}).get('num_train_epochs', 3),
            per_device_train_batch_size=yaml_config.get('training', {}).get('per_device_train_batch_size', 4),
            gradient_accumulation_steps=yaml_config.get('training', {}).get('gradient_accumulation_steps', 4),
            learning_rate=yaml_config.get('training', {}).get('learning_rate', 2e-4),
            max_length=yaml_config.get('training', {}).get('max_length', 1024),

            # Data paths
            train_data_path=yaml_config.get('data', {}).get('train_data_path', ''),
            valid_data_path=yaml_config.get('data', {}).get('valid_data_path', '')
        )

        return cls(config)


# 직접 실행 시
if __name__ == "__main__":
    # 방법 1: 기본 설정으로 실행
    # trainer = GemmaTrainer()

    # 방법 2: YAML 설정 파일로 실행
    # trainer = GemmaTrainer.from_yaml("configs/training_config.yaml")

    # 방법 3: 커스텀 설정으로 실행
    config = TrainingConfig(
        model_name="google/gemma-3-9b-it",
        train_data_path="data/processed/train.jsonl",  # TODO: 실제 경로
        valid_data_path="data/processed/valid.jsonl",  # TODO: 실제 경로
        num_train_epochs=3,
        output_dir="models/gemma_finetuned"
    )
    trainer = GemmaTrainer(config)

    # 학습 실행
    # model_path = trainer.train()
    print("학습 준비 완료. train_data_path를 설정하고 trainer.train()을 실행하세요.")
