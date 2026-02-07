#!/usr/bin/env python3
"""
Vertex AI Training Pipeline 제출 스크립트
Console에서 보이는 것과 동일한 Training Job 생성
"""

import os
from google.cloud import aiplatform
from datetime import datetime

# 서비스 계정 키 설정
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/Users/choidamul/GCPmodel/.gcp-key.json"

# 프로젝트 설정
PROJECT_ID = "knu-team-03"
LOCATION = "us-central1"  # A100 사용 가능 리전
BUCKET_NAME = "knu-team-03-data"

# 학습 설정
DISPLAY_NAME = f"gemma3-classical-lit-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

# Python 패키지 경로
PYTHON_PACKAGE_URI = f"gs://{BUCKET_NAME}/vertex-training-packages/gemma_classical_trainer-1.0.0.tar.gz"
PYTHON_MODULE = "trainer.train"

# 데이터 경로 (증강 데이터 사용)
TRAIN_DATA = f"gs://{BUCKET_NAME}/classical-literature/gemma/train_augmented.jsonl"
VALID_DATA = f"gs://{BUCKET_NAME}/classical-literature/gemma/valid_augmented.jsonl"
OUTPUT_DIR = f"gs://{BUCKET_NAME}/classical-literature/models/{DISPLAY_NAME}"

# HuggingFace 토큰 (환경변수에서 로드)
import os
HF_TOKEN = os.getenv("HUGGING_FACE_HUB_TOKEN", "")

# Container 설정 (PyTorch 2.4 + CUDA 12.1)
CONTAINER_URI = "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-4.py310:latest"

# Vertex AI 초기화
aiplatform.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=f"gs://{BUCKET_NAME}/staging"
)

print("=" * 60)
print("🚀 Vertex AI Training Pipeline 제출")
print("=" * 60)
print(f"프로젝트: {PROJECT_ID}")
print(f"리전: {LOCATION}")
print(f"Job 이름: {DISPLAY_NAME}")
print(f"패키지: {PYTHON_PACKAGE_URI}")
print(f"학습 데이터: {TRAIN_DATA}")
print(f"출력: {OUTPUT_DIR}")
print("=" * 60)

# CustomPythonPackageTrainingJob 생성
job = aiplatform.CustomPythonPackageTrainingJob(
    display_name=DISPLAY_NAME,
    python_package_gcs_uri=PYTHON_PACKAGE_URI,
    python_module_name=PYTHON_MODULE,
    container_uri=CONTAINER_URI,
)

print("\n🎯 Training Job 시작 중...")

# 학습 인자
args = [
    "--train-data", TRAIN_DATA,
    "--valid-data", VALID_DATA,
    "--output-dir", OUTPUT_DIR,
    "--hf-token", HF_TOKEN,
    "--model-name", "google/gemma-2-9b-it",
    "--epochs", "3",
    "--batch-size", "4",
    "--grad-accum", "4",
    "--learning-rate", "2e-4",
    "--max-seq-length", "1024",
]

# Job 실행 (A100 40GB)
model = job.run(
    args=args,
    replica_count=1,
    machine_type="a2-highgpu-1g",  # A100 40GB
    accelerator_type="NVIDIA_TESLA_A100",
    accelerator_count=1,
    base_output_dir=OUTPUT_DIR,
    sync=False,  # 비동기 실행 (백그라운드)
)

print("\n" + "=" * 60)
print("✅ Training Job 제출 완료!")
print("=" * 60)
print(f"Job 이름: {DISPLAY_NAME}")
print(f"\n📊 모니터링:")
print(f"Console: https://console.cloud.google.com/vertex-ai/training/training-pipelines?project={PROJECT_ID}")
print("\n⏱️ 예상 학습 시간: 1.5-2시간 (A100 40GB)")
print(f"💾 모델 저장 위치: {OUTPUT_DIR}")
print("\n💡 상태 확인:")
print(f"gcloud ai custom-jobs list --region={LOCATION} --filter='displayName:{DISPLAY_NAME}'")
print("=" * 60)
