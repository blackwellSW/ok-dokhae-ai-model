import argparse
import sys
import subprocess
from pathlib import Path
from datetime import datetime

from google.cloud import aiplatform

# ==============================================================================
# 🚀 [GCP 학습 발주서]
# 이 코드는 내 컴퓨터(Local)에서 구글 클라우드(GCP)로 학습 작업을 "지시"하는 역할을 합니다.
# 마치 배달 앱으로 음식을 주문하듯, "내 코드로 학습 좀 돌려줘!"라고 요청하는 스크립트입니다.
# ==============================================================================

# 상위 디렉토리 import를 위해 sys.path 추가
sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.gcp.config import (
    PROJECT_ID,
    REGION,
    BUCKET_NAME,
    GCS_DATA_PREFIX,
    GCS_MODEL_PREFIX,
    JOB_NAME,
    CONTAINER_URI,
    MACHINE_TYPE,
    REPLICA_COUNT,
)


def build_and_push_image(image_uri: str, dockerfile_path: str):
    """
    [1단계: 도시락 싸기 & 배달]
    우리 코드를 '도커(Docker)'라는 도시락통에 예쁘게 포장해서(Build),
    구글의 '공용 냉장고(Container Registry)'에 넣어두는(Push) 함수입니다.
    
    이렇게 해야 구글 컴퓨터가 우리 코드를 꺼내서 돌릴 수 있습니다.
    """
    print(f"🐳 [포장 중] 도커 이미지를 만들고 클라우드에 업로드합니다: {image_uri}...")
    # backend 디렉토리를 build context로 사용해야 하므로 부모 디렉토리로 이동
    backend_dir = Path(dockerfile_path).parent
    
    cmd = [
        "gcloud",
        "builds",
        "submit",
        str(backend_dir),
        f"--tag={image_uri}",
        f"--project={PROJECT_ID}",
    ]
    
    print(f"Running command: {' '.join(cmd)}")
    subprocess.check_call(cmd)
    print("✅ Image pushed successfully.")


def submit_custom_job(
    image_uri: str,
    bucket_name: str,
    data_prefix: str,
    model_prefix: str,
):
    """
    [2단계: 작업 지시하기]
    구글한테 무전기를 칩니다.
    "아까 냉장고에 넣은 그 도시락(Image) 꺼내서, 제일 좋은 컴퓨터로 학습 시작해!"
    """
    aiplatform.init(
        project=PROJECT_ID,
        location=REGION,
        staging_bucket=f"gs://{bucket_name}"
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    job_display_name = f"{JOB_NAME}_{timestamp}"
    
    # Arguments passed to the python script (train.py)
    args = [
        f"--train=gs://{bucket_name}/{data_prefix}/train.jsonl",
        f"--dev=gs://{bucket_name}/{data_prefix}/dev.jsonl",
        f"--test=gs://{bucket_name}/{data_prefix}/test.jsonl",
        f"--model-out=gs://{bucket_name}/{model_prefix}/{timestamp}/model.joblib",
    ]


    print(f"🚀 [발주 시작] Vertex AI에 학습 작업을 요청합니다: {job_display_name}")
    print(f"📋 [전달 인자] 학습 코드(train.py)에게 넘겨줄 설정값들: {args}")

    job = aiplatform.CustomContainerTrainingJob(
        display_name=job_display_name,
        container_uri=image_uri,
        # command=["python", "train.py"], # Dockerfile ENTRYPOINT 사용
    )

    model = job.run(
        args=args,                    # train.py한테 넘겨줄 변수들 (--train, --test 등)
        replica_count=REPLICA_COUNT,  # 컴퓨터 몇 대 빌릴지 (보통 1대면 충분)
        machine_type=MACHINE_TYPE,    # 어떤 사양의 컴퓨터를 빌릴지 (n1-standard-4 등)
        sync=False,                   # True면 끝날 때까지 여기서 기다리고, False면 주문 넣고 바로 퇴근! (비동기)
    )
    
    print(f"🎉 Job submitted! Check status at: https://console.cloud.google.com/vertex-ai/training/jobs?project={PROJECT_ID}")
    return job


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-build", action="store_true", help="Skip Docker build and use existing image")
    args = ap.parse_args()

    repo_root = Path(__file__).resolve().parents[2]
    dockerfile_path = repo_root / "backend" / "Dockerfile"

    if not args.skip_build:
        try:
            build_and_push_image(CONTAINER_URI, str(dockerfile_path))
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to build image: {e}")
            return

    # 스크립트 실행 흐름:
    # 1. 도커 이미지 빌드/푸시 (Skip 옵션 없으면 무조건 실행)
    # 2. Vertex AI에 학습 작업 제출
    submit_custom_job(
        image_uri=CONTAINER_URI,
        bucket_name=BUCKET_NAME,
        data_prefix=GCS_DATA_PREFIX,
        model_prefix=GCS_MODEL_PREFIX,
    )


if __name__ == "__main__":
    main()
