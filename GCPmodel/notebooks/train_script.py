#!/usr/bin/env python3
"""
Gemma 3 9B Fine-tuning - 백그라운드 실행용 스크립트
와이파이 끊겨도 안전하게 학습 진행
"""

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
from trl import SFTTrainer
import os

print("="*60)
print("Gemma 3 9B Fine-tuning 시작")
print("="*60)

# 환경 확인
print(f"\nPyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")

# 데이터셋 로드
print("\n데이터셋 로드 중...")
train_dataset = load_dataset('json', data_files='train_balanced.jsonl', split='train')
valid_dataset = load_dataset('json', data_files='valid_balanced.jsonl', split='train')
print(f"Train: {len(train_dataset)}개, Valid: {len(valid_dataset)}개")

# Hugging Face 로그인
from huggingface_hub import login
import os
HF_TOKEN = os.getenv("HUGGING_FACE_HUB_TOKEN")
if HF_TOKEN:
    login(token=HF_TOKEN)
    print("✅ HuggingFace 로그인 완료")
else:
    print("⚠️ HUGGING_FACE_HUB_TOKEN 환경변수를 설정하세요")

# 모델 로드
print("\n모델 로드 중... (3-5분 소요)")
model_name = "google/gemma-2-9b-it"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

model = AutoModelForCausalLM.from_pretrained(
    model_name,
    quantization_config=bnb_config,
    device_map="auto",
    trust_remote_code=True,
    attn_implementation="eager"
)

tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"
print("✅ 모델 로드 완료")

# LoRA 설정
print("\nLoRA 설정 중...")
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
print("✅ LoRA 설정 완료")

# 데이터 포맷팅
def formatting_func(examples):
    texts = []
    for instruction, input_text, output in zip(examples['instruction'], examples['input'], examples['output']):
        text = f"""<start_of_turn>user
{instruction}

{input_text}<end_of_turn>
<start_of_turn>model
{output}<end_of_turn>"""
        texts.append(text)
    return texts

# Trainer 설정
print("\nTrainer 설정 중...")
output_dir = "./gemma3-classical-lit-finetuned"

training_args = TrainingArguments(
    output_dir=output_dir,
    num_train_epochs=3,
    per_device_train_batch_size=1,
    per_device_eval_batch_size=1,
    gradient_accumulation_steps=16,
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_ratio=0.03,
    logging_steps=10,
    eval_strategy="steps",
    eval_steps=50,
    save_strategy="steps",
    save_steps=500,
    save_total_limit=1,
    bf16=True,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},
    max_grad_norm=1.0,
    dataloader_num_workers=2,
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
    max_seq_length=512,
    dataset_text_field=None,
    tokenizer=tokenizer,
)
print("✅ Trainer 설정 완료")

# 학습 시작
print("\n" + "="*60)
print("🚀 학습 시작!")
print("="*60)
trainer.train()

print("\n" + "="*60)
print("✅ 학습 완료!")
print("="*60)

# 모델 저장
print("\n모델 저장 중...")
trainer.save_model(output_dir)
tokenizer.save_pretrained(output_dir)
print(f"✅ 로컬 저장 완료: {output_dir}")

# Cloud Storage 업로드
print("\nCloud Storage 업로드 중...")
import subprocess
subprocess.run([
    "gsutil", "-m", "cp", "-r",
    output_dir,
    "gs://knu-team-03-data/classical-literature/models/"
])
print("✅ Cloud Storage 업로드 완료!")

print("\n" + "="*60)
print("🎉 모든 작업 완료!")
print("="*60)
