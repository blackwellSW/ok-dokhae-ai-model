#!/usr/bin/env python3
"""
Vertex AI Training Pipeline으로 Gemma 3 파인튜닝
- 완전 자동화
- 브라우저 불필요
- A100 GPU 사용
"""

from google.cloud import aiplatform
from datetime import datetime

# 프로젝트 설정
PROJECT_ID = "knu-team-03"
LOCATION = "us-central1"
BUCKET_NAME = "knu-team-03-data"

# 학습 설정
DISPLAY_NAME = f"gemma3-classical-lit-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
CONTAINER_URI = "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-4.py310:latest"

# 데이터 경로
TRAIN_DATA = f"gs://{BUCKET_NAME}/classical-literature/gemma/train_balanced.jsonl"
VALID_DATA = f"gs://{BUCKET_NAME}/classical-literature/gemma/valid_balanced.jsonl"
OUTPUT_DIR = f"gs://{BUCKET_NAME}/classical-literature/models/{DISPLAY_NAME}"

# HuggingFace 토큰
HF_TOKEN = "YOUR_HF_TOKEN_HERE"

# Vertex AI 초기화
aiplatform.init(project=PROJECT_ID, location=LOCATION, staging_bucket=f"gs://{BUCKET_NAME}/staging")

print("="*60)
print("🚀 Vertex AI Training Pipeline 시작")
print("="*60)
print(f"프로젝트: {PROJECT_ID}")
print(f"리전: {LOCATION}")
print(f"Job 이름: {DISPLAY_NAME}")
print(f"학습 데이터: {TRAIN_DATA}")
print(f"출력 디렉토리: {OUTPUT_DIR}")
print("="*60)

# 학습 스크립트 (컨테이너 내부에서 실행됨)
TRAINING_SCRIPT = """
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from datasets import load_dataset
from trl import SFTTrainer
from huggingface_hub import login
import sys

# HuggingFace 로그인
login(token="{hf_token}")

# 데이터 로드
print("📊 데이터 로드 중...")
train_dataset = load_dataset('json', data_files='{train_data}', split='train')
valid_dataset = load_dataset('json', data_files='{valid_data}', split='train')
print(f"✅ Train: {len(train_dataset)}, Valid: {len(valid_dataset)}")

# 모델 로드
print("🤖 모델 로드 중...")
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
print("🔧 LoRA 설정 중...")
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

# 데이터 포맷팅
def formatting_func(examples):
    texts = []
    for instruction, input_text, output in zip(examples['instruction'], examples['input'], examples['output']):
        text = f\"\"\"<start_of_turn>user
{{instruction}}

{{input_text}}<end_of_turn>
<start_of_turn>model
{{output}}<end_of_turn>\"\"\"
        texts.append(text)
    return texts

# Trainer 설정 (A100 최적화)
print("⚙️ Trainer 설정 중...")
training_args = TrainingArguments(
    output_dir="{output_dir}",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    gradient_accumulation_steps=4,
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
    tf32=True,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={{"use_reentrant": False}},
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
    max_seq_length=1024,
    dataset_text_field=None,
    tokenizer=tokenizer,
)

# 학습 시작
print("="*60)
print("🚀 학습 시작!")
print("="*60)
trainer.train()

# 모델 저장
print("💾 모델 저장 중...")
trainer.save_model("{output_dir}")
tokenizer.save_pretrained("{output_dir}")
print("✅ 학습 완료!")
"""

# 스크립트를 파일로 저장 (컨테이너에서 실행)
script_content = TRAINING_SCRIPT.format(
    hf_token=HF_TOKEN,
    train_data=TRAIN_DATA,
    valid_data=VALID_DATA,
    output_dir=OUTPUT_DIR
)

# GCS에 스크립트 업로드
import tempfile
import os
from google.cloud import storage

with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
    f.write(script_content)
    script_path = f.name

# Upload to GCS
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(BUCKET_NAME)
blob = bucket.blob(f"staging/train_script_{datetime.now().strftime('%Y%m%d_%H%M%S')}.py")
blob.upload_from_filename(script_path)
script_uri = f"gs://{BUCKET_NAME}/{blob.name}"
os.unlink(script_path)

print(f"📤 학습 스크립트 업로드: {script_uri}")

# Custom Job 생성
job = aiplatform.CustomPythonPackageTrainingJob(
    display_name=DISPLAY_NAME,
    python_package_gcs_uri=script_uri,
    python_module_name="train_script",
    container_uri=CONTAINER_URI,
)

print("\n🎯 Training Job 시작 중...")

# Job 실행
model = job.run(
    replica_count=1,
    machine_type="a2-highgpu-1g",  # A100 40GB
    accelerator_type="NVIDIA_TESLA_A100",
    accelerator_count=1,
    base_output_dir=OUTPUT_DIR,
    sync=True,  # 동기 실행 (완료까지 대기)
)

print("\n" + "="*60)
print("✅ Training Pipeline 완료!")
print("="*60)
print(f"모델 저장 위치: {OUTPUT_DIR}")
print(f"\n모니터링:")
print(f"https://console.cloud.google.com/vertex-ai/training/training-pipelines?project={PROJECT_ID}")
print("="*60)
