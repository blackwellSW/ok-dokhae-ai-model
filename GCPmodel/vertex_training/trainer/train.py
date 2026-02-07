#!/usr/bin/env python3
"""
Vertex AI Training Pipeline용 학습 스크립트
완전히 독립적으로 실행 가능
"""

# Gemma 3 지원을 위해 최신 패키지 설치
import subprocess
import sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "--upgrade",
                       "transformers>=4.49.0", "accelerate>=0.34.0", "peft>=0.14.0", "trl>=0.12.0", "bitsandbytes>=0.46.1"])

import os
import argparse
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
from trl import SFTTrainer
from huggingface_hub import login
from google.cloud import storage

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--train-data", type=str, required=True, help="GCS path to train data")
    parser.add_argument("--valid-data", type=str, required=True, help="GCS path to valid data")
    parser.add_argument("--output-dir", type=str, required=True, help="GCS path to output directory")
    parser.add_argument("--hf-token", type=str, required=True, help="HuggingFace token")
    parser.add_argument("--model-name", type=str, default="google/gemma-3-12b-it")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--grad-accum", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--max-seq-length", type=int, default=1024)
    return parser.parse_args()

def download_from_gcs(gcs_path, local_path):
    """GCS에서 파일 다운로드"""
    if not gcs_path.startswith("gs://"):
        return gcs_path

    bucket_name = gcs_path.split("/")[2]
    blob_path = "/".join(gcs_path.split("/")[3:])

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(blob_path)
    blob.download_to_filename(local_path)

    return local_path

def formatting_func(examples):
    """Gemma 형식으로 데이터 포맷팅 (input_text, output_text 형식 지원)"""
    texts = []

    # 새로운 형식 (input_text, output_text)
    if 'input_text' in examples:
        for input_text, output_text in zip(examples['input_text'], examples['output_text']):
            text = f"""<start_of_turn>user
{input_text}<end_of_turn>
<start_of_turn>model
{output_text}<end_of_turn>"""
            texts.append(text)
    # 기존 형식 (instruction, input, output)
    else:
        for instruction, input_text, output in zip(examples['instruction'], examples['input'], examples['output']):
            text = f"""<start_of_turn>user
{instruction}

{input_text}<end_of_turn>
<start_of_turn>model
{output}<end_of_turn>"""
            texts.append(text)
    return texts

def main():
    args = parse_args()

    print("=" * 60)
    print("🚀 Vertex AI Training Pipeline - Gemma 3 Fine-tuning")
    print("=" * 60)
    print(f"Model: {args.model_name}")
    print(f"Train data: {args.train_data}")
    print(f"Output: {args.output_dir}")
    print("=" * 60)

    # HuggingFace 로그인
    print("\n🔐 HuggingFace 로그인...")
    login(token=args.hf_token)
    print("✅ 로그인 완료")

    # 데이터 다운로드
    print("\n📥 데이터 다운로드...")
    train_local = "/tmp/train_balanced.jsonl"
    valid_local = "/tmp/valid_balanced.jsonl"

    download_from_gcs(args.train_data, train_local)
    download_from_gcs(args.valid_data, valid_local)

    # 데이터셋 로드
    print("\n📊 데이터셋 로드...")
    train_dataset = load_dataset('json', data_files=train_local, split='train')
    valid_dataset = load_dataset('json', data_files=valid_local, split='train')
    print(f"✅ Train: {len(train_dataset)}, Valid: {len(valid_dataset)}")

    # GPU 확인
    print("\n🔥 GPU 확인...")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"Memory: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.2f} GB")

    # 모델 로드
    print("\n🤖 모델 로드 중...")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16
    )

    model = AutoModelForCausalLM.from_pretrained(
        args.model_name,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
        attn_implementation="eager"
    )

    tokenizer = AutoTokenizer.from_pretrained(args.model_name, trust_remote_code=True)
    tokenizer.pad_token = tokenizer.eos_token
    tokenizer.padding_side = "right"
    print("✅ 모델 로드 완료")

    # LoRA 설정
    print("\n🔧 LoRA 설정...")
    peft_config = LoraConfig(
        lora_alpha=32,
        lora_dropout=0.1,
        r=16,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
    )

    model = prepare_model_for_kbit_training(model)
    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # Trainer 설정
    print("\n⚙️ Trainer 설정...")
    local_output_dir = "/tmp/output"
    os.makedirs(local_output_dir, exist_ok=True)

    training_args = TrainingArguments(
        output_dir=local_output_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.learning_rate,
        lr_scheduler_type="cosine",
        warmup_ratio=0.03,
        logging_steps=10,
        eval_strategy="steps",
        eval_steps=50,
        save_strategy="steps",
        save_steps=500,
        save_total_limit=2,
        bf16=True,
        tf32=True,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        max_grad_norm=1.0,
        dataloader_num_workers=4,
        dataloader_pin_memory=True,
        report_to="none",
        load_best_model_at_end=False,
    )

    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=valid_dataset,
        formatting_func=formatting_func,
        packing=False,
        max_seq_length=args.max_seq_length,
        dataset_text_field=None,
        tokenizer=tokenizer,
    )

    # 학습 시작
    print("\n" + "=" * 60)
    print("🚀 학습 시작!")
    print("=" * 60)
    trainer.train()

    # 모델 저장
    print("\n💾 모델 저장 중...")
    trainer.save_model(local_output_dir)
    tokenizer.save_pretrained(local_output_dir)
    print(f"✅ 로컬 저장 완료: {local_output_dir}")

    # GCS에 업로드
    print(f"\n📤 GCS 업로드 중: {args.output_dir}")
    import subprocess
    subprocess.run([
        "gsutil", "-m", "cp", "-r",
        f"{local_output_dir}/*",
        args.output_dir
    ], check=True)

    print("\n" + "=" * 60)
    print("✅ 학습 완료!")
    print("=" * 60)
    print(f"모델 저장 위치: {args.output_dir}")

if __name__ == "__main__":
    main()
