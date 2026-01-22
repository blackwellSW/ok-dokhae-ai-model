import argparse
import sys
from pathlib import Path

from google.cloud import storage

# 상위 디렉토리 import를 위해 sys.path 추가
sys.path.append(str(Path(__file__).resolve().parents[2]))

from backend.gcp.config import BUCKET_NAME, GCS_DATA_PREFIX, PROJECT_ID


def upload_to_gcs(source_file: Path, destination_blob_name: str) -> None:
    """Uploads a file to the bucket."""
    storage_client = storage.Client(project=PROJECT_ID)
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)

    print(f"Uploading {source_file} to gs://{BUCKET_NAME}/{destination_blob_name}...")
    blob.upload_from_filename(str(source_file))
    print(f"File uploaded to gs://{BUCKET_NAME}/{destination_blob_name}")


def main():
    repo_root = Path(__file__).resolve().parents[2]
    data_dir = repo_root / "data" / "processed" / "dm"

    files_to_upload = [
        "train.jsonl",
        "dev.jsonl",
        "test.jsonl"
    ]

    print(f"🚀 Starting upload to GCS Bucket: {BUCKET_NAME}")
    
    for filename in files_to_upload:
        local_path = data_dir / filename
        if not local_path.exists():
            print(f"⚠️ Warning: {local_path} does not exist. Skipping.")
            continue
            
        gcs_path = f"{GCS_DATA_PREFIX}/{filename}"
        try:
            upload_to_gcs(local_path, gcs_path)
        except Exception as e:
            print(f"❌ Failed to upload {filename}: {e}")
            print("Tip: 'gcloud auth application-default login'이 되어 있는지 확인해보세요!")
            return

    print("✅ All uploads completed successfully!")


if __name__ == "__main__":
    main()
