FROM python:3.11-slim

# 파이썬 출력 로그가 즉시 보이게 설정
ENV PYTHONUNBUFFERED=1
# HuggingFace 모델 캐시 경로 설정 (빌드 시 저장된 모델을 런타임에도 사용)
ENV HF_HOME=/app/model_cache

# 작업 디렉토리 설정
WORKDIR /app

# 1. 시스템 의존성 설치 (필요한 경우)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 2. Python 라이브러리 설치
# CPU 전용 Torch 먼저 설치 (이미지 크기 최적화)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# 나머지 라이브러리 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 3. AI 모델 다운로드 (빌드 타임에 실행하여 이미지에 포함시킴)
COPY download_model.py .
RUN python download_model.py

# 4. 전체 파일 복사 (키 파일 포함)
COPY . .

# 파이썬 경로 설정
ENV PYTHONPATH=/app

# 8080 포트에서 실행
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--timeout-keep-alive", "120"]