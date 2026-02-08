"""
GCP 유틸리티 모듈
Vertex AI, Cloud Storage 연동
"""

import os
from pathlib import Path
from typing import Optional, Dict, List


class GCPManager:
    """GCP 서비스 관리 클래스"""

    def __init__(
        self,
        project_id: str = "",  # TODO: GCP 프로젝트 ID
        region: str = "us-central1",
        bucket_name: str = ""  # TODO: Cloud Storage 버킷 이름
    ):
        """
        Args:
            project_id: GCP 프로젝트 ID
            region: GCP 리전
            bucket_name: Cloud Storage 버킷 이름
        """
        self.project_id = project_id or os.getenv("GCP_PROJECT_ID", "")
        self.region = region
        self.bucket_name = bucket_name or os.getenv("GCP_BUCKET_NAME", "")

        self.storage_client = None
        self.vertex_ai_initialized = False

        if self.project_id:
            self._init_clients()

    def _init_clients(self):
        """GCP 클라이언트 초기화"""
        # Cloud Storage
        try:
            from google.cloud import storage
            self.storage_client = storage.Client(project=self.project_id)
            print(f"✅ Cloud Storage 클라이언트 초기화 완료")
        except ImportError:
            print("⚠️ google-cloud-storage 패키지를 설치해주세요.")
        except Exception as e:
            print(f"⚠️ Cloud Storage 초기화 실패: {e}")

        # Vertex AI
        try:
            from google.cloud import aiplatform
            aiplatform.init(project=self.project_id, location=self.region)
            self.vertex_ai_initialized = True
            print(f"✅ Vertex AI 초기화 완료 (리전: {self.region})")
        except ImportError:
            print("⚠️ google-cloud-aiplatform 패키지를 설치해주세요.")
        except Exception as e:
            print(f"⚠️ Vertex AI 초기화 실패: {e}")

    def upload_to_gcs(
        self,
        local_path: str,
        gcs_path: str,
        bucket_name: Optional[str] = None
    ) -> str:
        """
        파일을 Cloud Storage에 업로드

        Args:
            local_path: 로컬 파일 경로
            gcs_path: GCS 내 경로 (예: "data/train.jsonl")
            bucket_name: 버킷 이름 (None이면 기본 버킷)

        Returns:
            str: GCS URI (gs://bucket/path)
        """
        if not self.storage_client:
            print("⚠️ Cloud Storage 클라이언트가 초기화되지 않았습니다.")
            return ""

        bucket_name = bucket_name or self.bucket_name
        if not bucket_name:
            print("⚠️ 버킷 이름이 설정되지 않았습니다.")
            return ""

        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(gcs_path)
            blob.upload_from_filename(local_path)

            gcs_uri = f"gs://{bucket_name}/{gcs_path}"
            print(f"✅ 업로드 완료: {gcs_uri}")
            return gcs_uri

        except Exception as e:
            print(f"❌ 업로드 실패: {e}")
            return ""

    def download_from_gcs(
        self,
        gcs_path: str,
        local_path: str,
        bucket_name: Optional[str] = None
    ) -> bool:
        """
        Cloud Storage에서 파일 다운로드

        Args:
            gcs_path: GCS 내 경로
            local_path: 로컬 저장 경로
            bucket_name: 버킷 이름

        Returns:
            bool: 성공 여부
        """
        if not self.storage_client:
            print("⚠️ Cloud Storage 클라이언트가 초기화되지 않았습니다.")
            return False

        bucket_name = bucket_name or self.bucket_name

        try:
            bucket = self.storage_client.bucket(bucket_name)
            blob = bucket.blob(gcs_path)

            # 로컬 디렉토리 생성
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)

            blob.download_to_filename(local_path)
            print(f"✅ 다운로드 완료: {local_path}")
            return True

        except Exception as e:
            print(f"❌ 다운로드 실패: {e}")
            return False

    def list_gcs_files(
        self,
        prefix: str = "",
        bucket_name: Optional[str] = None
    ) -> List[str]:
        """
        GCS 버킷 내 파일 목록 조회

        Args:
            prefix: 경로 prefix
            bucket_name: 버킷 이름

        Returns:
            List[str]: 파일 경로 리스트
        """
        if not self.storage_client:
            return []

        bucket_name = bucket_name or self.bucket_name

        try:
            bucket = self.storage_client.bucket(bucket_name)
            blobs = bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            print(f"❌ 목록 조회 실패: {e}")
            return []

    def create_vertex_training_job(
        self,
        display_name: str,
        script_path: str,
        requirements_path: str,
        machine_type: str = "n1-standard-8",
        accelerator_type: str = "NVIDIA_TESLA_A100",
        accelerator_count: int = 1,
        args: Optional[List[str]] = None
    ) -> Optional[str]:
        """
        Vertex AI 학습 작업 생성

        Args:
            display_name: 작업 이름
            script_path: 학습 스크립트 경로
            requirements_path: requirements.txt 경로
            machine_type: 머신 타입
            accelerator_type: GPU 타입
            accelerator_count: GPU 개수
            args: 스크립트 인자

        Returns:
            str: 작업 ID (또는 None)
        """
        if not self.vertex_ai_initialized:
            print("⚠️ Vertex AI가 초기화되지 않았습니다.")
            return None

        try:
            from google.cloud import aiplatform

            job = aiplatform.CustomJob.from_local_script(
                display_name=display_name,
                script_path=script_path,
                requirements=[requirements_path],
                container_uri="us-docker.pkg.dev/vertex-ai/training/pytorch-gpu.1-13:latest",
                machine_type=machine_type,
                accelerator_type=accelerator_type,
                accelerator_count=accelerator_count,
                args=args or []
            )

            job.run(sync=False)
            print(f"✅ 학습 작업 시작: {job.resource_name}")
            return job.resource_name

        except Exception as e:
            print(f"❌ 학습 작업 생성 실패: {e}")
            return None

    def get_training_job_status(self, job_name: str) -> Dict:
        """
        학습 작업 상태 조회

        Args:
            job_name: 작업 리소스 이름

        Returns:
            Dict: 상태 정보
        """
        if not self.vertex_ai_initialized:
            return {"status": "NOT_INITIALIZED"}

        try:
            from google.cloud import aiplatform
            job = aiplatform.CustomJob(job_name=job_name)

            return {
                "status": job.state.name,
                "display_name": job.display_name,
                "create_time": str(job.create_time),
                "update_time": str(job.update_time)
            }

        except Exception as e:
            return {"status": "ERROR", "error": str(e)}

    def upload_model_to_vertex(
        self,
        model_path: str,
        display_name: str,
        serving_container_uri: str = "us-docker.pkg.dev/vertex-ai/prediction/pytorch-gpu.1-13:latest"
    ) -> Optional[str]:
        """
        학습된 모델을 Vertex AI Model Registry에 업로드

        Args:
            model_path: 모델 파일 경로 (GCS 경로)
            display_name: 모델 이름
            serving_container_uri: 서빙 컨테이너 URI

        Returns:
            str: 모델 리소스 이름
        """
        if not self.vertex_ai_initialized:
            print("⚠️ Vertex AI가 초기화되지 않았습니다.")
            return None

        try:
            from google.cloud import aiplatform

            model = aiplatform.Model.upload(
                display_name=display_name,
                artifact_uri=model_path,
                serving_container_image_uri=serving_container_uri
            )

            print(f"✅ 모델 업로드 완료: {model.resource_name}")
            return model.resource_name

        except Exception as e:
            print(f"❌ 모델 업로드 실패: {e}")
            return None


# 직접 실행 시
if __name__ == "__main__":
    # 테스트
    gcp = GCPManager(
        project_id="",  # TODO: 프로젝트 ID
        bucket_name=""  # TODO: 버킷 이름
    )

    print("GCP 매니저 준비 완료. project_id와 bucket_name을 설정하고 사용하세요.")
