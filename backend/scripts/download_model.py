import os
from sentence_transformers import SentenceTransformer

def download_model():
    model_name = 'snunlp/KR-SBERT-V40K-klueNLI-augSTS'
    print(f"Downloading model: {model_name}...")
    
    # 캐시 디렉토리는 환경 변수 또는 기본값 사용
    # Dockerfile에서 ENV HF_HOME=/app/model_cache 로 설정할 예정
    model = SentenceTransformer(model_name)
    print("Model downloaded successfully!")

if __name__ == "__main__":
    download_model()
