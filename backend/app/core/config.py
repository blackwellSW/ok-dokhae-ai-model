"""
app/core/config.py
역할: 전역 환경 설정 및 변수 관리
"""
import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # API 설정
    PROJECT_NAME: str = "고전문학 사고유도 AI 학습 시스템"
    DEBUG: bool = True

    # Firebase 설정
    FIREBASE_PROJECT_ID: str = os.getenv("FIREBASE_PROJECT_ID", "knu-team-03")

    # 데이터베이스 설정
    # Cloud Run: /tmp is writable, use in-memory for stateless
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite+aiosqlite:////tmp/test.db"  # 절대 경로는 슬래시 4개 필요
    )

    # AI 모델 설정
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    # Vertex AI 설정 (Fine-tuned Gemma 3 Model via vLLM)
    VERTEX_AI_ENDPOINT: str = os.getenv(
        "VERTEX_AI_ENDPOINT",
        "https://us-central1-aiplatform.googleapis.com/v1/projects/knu-team-03/locations/us-central1/endpoints/2283851677146546176:rawPredict"
    )
    VERTEX_AI_MODEL: str = os.getenv("VERTEX_AI_MODEL", "classical-lit")
    USE_VERTEX_AI: bool = os.getenv("USE_VERTEX_AI", "true").lower() == "true"

    # Google Cloud Document AI 설정
    # 프로세서 ID는 GCP 콘솔에서 생성 후 설정
    # 서비스 계정은 GOOGLE_APPLICATION_CREDENTIALS 환경변수로 설정
    DOCUMENT_AI_PROCESSOR_ID: str = os.getenv("DOCUMENT_AI_PROCESSOR_ID", "")
    DOCUMENT_AI_LOCATION: str = os.getenv("DOCUMENT_AI_LOCATION", "asia-northeast1")

    # 인증 설정
    GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-super-secret-key-change-in-production")

    # CORS 설정 (쉼표로 구분된 도메인 목록)
    # 예: "http://localhost:3000,http://localhost:5173,https://myapp.web.app"
    CORS_ORIGINS: str = os.getenv("CORS_ORIGINS", "")

    # 평가 설정
    QUALITATIVE_WEIGHT: float = 0.7  # 질적 평가 가중치 70%
    QUANTITATIVE_WEIGHT: float = 0.3  # 정량 평가 가중치 30%

    model_config = SettingsConfigDict(env_file=".env")

    def get_cors_origins(self) -> list:
        """
        CORS 허용 도메인 목록 반환

        - CORS_ORIGINS가 비어있거나 "*"이면 빈 리스트 반환 (개발 모드)
        - main.py에서 빈 리스트면 allow_origins=["*"], credentials=False 사용
        - 프로덕션에서는 CORS_ORIGINS에 도메인 명시 필요
        """
        if not self.CORS_ORIGINS or self.CORS_ORIGINS.strip() == "*":
            # 개발 모드: 빈 리스트 반환 → main.py에서 "*" 사용
            return []
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

settings = Settings()

def get_settings() -> Settings:
    """설정 객체 반환 (의존성 주입용)"""
    return settings
