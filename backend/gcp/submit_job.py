import argparse
import sys
import subprocess
from pathlib import Path
from datetime import datetime

from google.cloud import aiplatform

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
    """Builds and pushes the Docker image using Cloud Build."""
    print(f"🐳 Building and pushing Docker image to {image_uri}...")
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
    """Submits a Custom Training Job to Vertex AI."""
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

    print(f"🚀 Submitting Custom Job: {job_display_name}")
    print(f"Arguments: {args}")

    job = aiplatform.CustomContainerTrainingJob(
        display_name=job_display_name,
        container_uri=image_uri,
        # command=["python", "train.py"], # Dockerfile ENTRYPOINT 사용
    )

    model = job.run(
        args=args,
        replica_count=REPLICA_COUNT,
        machine_type=MACHINE_TYPE,
        sync=False, # 비동기 실행 (Logs는 콘솔에서 확인)
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

    submit_custom_job(
        image_uri=CONTAINER_URI,
        bucket_name=BUCKET_NAME,
        data_prefix=GCS_DATA_PREFIX,
        model_prefix=GCS_MODEL_PREFIX,
    )


if __name__ == "__main__":
    main()
