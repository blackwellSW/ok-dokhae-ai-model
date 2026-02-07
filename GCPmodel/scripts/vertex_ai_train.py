#!/usr/bin/env python3
"""
Vertex AI Custom Training Job 생성 및 실행
"""

import argparse
from google.cloud import aiplatform


def create_training_job(
    project_id: str,
    location: str,
    display_name: str,
    train_data_uri: str,
    valid_data_uri: str,
    output_dir_uri: str,
    machine_type: str = "n1-standard-16",
    accelerator_type: str = "NVIDIA_H100_MEGA_80GB",
    accelerator_count: int = 2,
):
    """
    Vertex AI Custom Training Job 생성

    Args:
        project_id: GCP 프로젝트 ID
        location: 리전 (예: asia-northeast1)
        display_name: Job 이름
        train_data_uri: 학습 데이터 GCS 경로
        valid_data_uri: 검증 데이터 GCS 경로
        output_dir_uri: 출력 디렉토리 GCS 경로
        machine_type: 머신 타입
        accelerator_type: GPU 타입
        accelerator_count: GPU 개수
    """

    # Vertex AI 초기화
    aiplatform.init(project=project_id, location=location)

    # 학습 스크립트 및 패키지 경로
    # 여기서는 사전 빌드된 PyTorch 컨테이너를 사용
    container_uri = "us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.2-2.py310:latest"

    # 학습 스크립트 인자
    args = [
        "--train-data", train_data_uri,
        "--valid-data", valid_data_uri,
        "--output-dir", output_dir_uri,
        "--model-name", "google/gemma-2-9b-it",
        "--epochs", "3",
        "--batch-size", "4",
        "--learning-rate", "2e-4",
        "--max-length", "1024",
        "--lora-r", "16",
        "--lora-alpha", "32",
    ]

    # Custom Training Job 생성
    job = aiplatform.CustomContainerTrainingJob(
        display_name=display_name,
        container_uri=container_uri,
    )

    print(f"Creating training job: {display_name}")
    print(f"Location: {location}")
    print(f"Machine: {machine_type}")
    print(f"Accelerator: {accelerator_type} x {accelerator_count}")
    print(f"Train data: {train_data_uri}")
    print(f"Output: {output_dir_uri}")

    # Job 실행
    model = job.run(
        args=args,
        replica_count=1,
        machine_type=machine_type,
        accelerator_type=accelerator_type,
        accelerator_count=accelerator_count,
        base_output_dir=output_dir_uri,
        sync=False,  # 비동기 실행
    )

    print(f"\n✅ Training job submitted!")
    print(f"Job ID: {job.resource_name}")
    print(f"\n모니터링:")
    print(f"Console: https://console.cloud.google.com/vertex-ai/training/custom-jobs?project={project_id}")

    return job


def main():
    parser = argparse.ArgumentParser(description="Vertex AI Training Job 생성")

    parser.add_argument("--project-id", type=str, default="knu-team-03", help="GCP 프로젝트 ID")
    parser.add_argument("--location", type=str, default="asia-northeast1", help="리전")
    parser.add_argument("--display-name", type=str, default="gemma3-classical-lit", help="Job 이름")
    parser.add_argument("--train-data", type=str,
                       default="gs://knu-team-03-data/classical-literature/gemma/train_gemma.jsonl",
                       help="학습 데이터 GCS 경로")
    parser.add_argument("--valid-data", type=str,
                       default="gs://knu-team-03-data/classical-literature/gemma/valid_gemma.jsonl",
                       help="검증 데이터 GCS 경로")
    parser.add_argument("--output-dir", type=str,
                       default="gs://knu-team-03-data/classical-literature/models",
                       help="출력 디렉토리 GCS 경로")
    parser.add_argument("--machine-type", type=str, default="n1-standard-16", help="머신 타입")
    parser.add_argument("--accelerator-type", type=str, default="NVIDIA_H100_MEGA_80GB",
                       help="GPU 타입")
    parser.add_argument("--accelerator-count", type=int, default=2, help="GPU 개수")

    args = parser.parse_args()

    create_training_job(
        project_id=args.project_id,
        location=args.location,
        display_name=args.display_name,
        train_data_uri=args.train_data,
        valid_data_uri=args.valid_data,
        output_dir_uri=args.output_dir,
        machine_type=args.machine_type,
        accelerator_type=args.accelerator_type,
        accelerator_count=args.accelerator_count,
    )


if __name__ == "__main__":
    main()
