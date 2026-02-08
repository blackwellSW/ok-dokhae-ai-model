# Python 3.10 슬림 이미지 사용
FROM python:3.10-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 의존성 설치 (PostgreSQL 등)
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*

# 패키지 설치 최적화를 위해 requirements.txt 먼저 복사
COPY requirements.txt .

# 패키지 설치 (캐시 활용)
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# Cloud Run은 PORT 환경변수를 제공하므로 그 포트로 실행
ENV PORT=8080
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
