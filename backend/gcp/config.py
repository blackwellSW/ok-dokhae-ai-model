import os

# Google Cloud Project Settings
# TODO: 사용자분께서 직접 수정해주셔야 하는 부분입니다!
PROJECT_ID = "knu-team-03"  # 스크린샷 기반 업데이트
REGION = "asia-northeast1"  # 버킷 위치(도쿄)와 동일하게 설정
BUCKET_NAME = "okdockhae-storage" # 스크린샷 기반 업데이트

# Paths in GCS
GCS_DATA_PREFIX = "data/dm/v1"
GCS_MODEL_PREFIX = "models/dm"

# Training Job Settings
JOB_NAME = "ok-dokhae-dm-train-v1"
CONTAINER_URI = f"asia-northeast1-docker.pkg.dev/{PROJECT_ID}/dm-repo/train:latest"
MACHINE_TYPE = "n1-standard-4"
REPLICA_COUNT = 1
