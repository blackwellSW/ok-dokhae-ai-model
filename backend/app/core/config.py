"""
app/core/config.py
역할: 전역 환경 설정 및 변수 관리
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API 설정
    PROJECT_NAME: str = "고전문학 사고유도 AI 학습 시스템"
    
    # 데이터베이스 설정
    # Cloud Run: /tmp is writable, use in-memory for stateless
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite+aiosqlite:///tmp/test.db"  # Use /tmp which is writable in Cloud Run
    )
    
    # AI 모델 설정
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    
    # Google Cloud Document AI 설정
    # 프로세서 ID는 GCP 콘솔에서 생성 후 설정
    # 서비스 계정은 GOOGLE_APPLICATION_CREDENTIALS 환경변수로 설정
    DOCUMENT_AI_PROCESSOR_ID: str = os.getenv("DOCUMENT_AI_PROCESSOR_ID", "")
    DOCUMENT_AI_LOCATION: str = os.getenv("DOCUMENT_AI_LOCATION", "asia-northeast1")
    
    # 인증 설정 (Google OAuth)
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    
    # 평가 설정
    QUALITATIVE_WEIGHT: float = 0.7  # 질적 평가 가중치 70%
    QUANTITATIVE_WEIGHT: float = 0.3  # 정량 평가 가중치 30%

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

def get_settings() -> Settings:
    """설정 객체 반환 (의존성 주입용)"""
    return settings
