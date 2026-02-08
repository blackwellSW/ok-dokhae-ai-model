"""
app/db/database.py
역할: 비동기 DB 엔진 생성 및 세션 팩토리 설정
"""
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Check if using SQLite (for Cloud Run compatibility)
is_sqlite = settings.DATABASE_URL.startswith("sqlite")

# 엔진 생성
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=True,
    future=True,
    # pool_pre_ping only works with connection pooling (not SQLite)
    pool_pre_ping=False if is_sqlite else True,
    # For in-memory SQLite, we need to share connections
    connect_args={"check_same_thread": False} if is_sqlite else {}
)

# 비동기 세션 생성기
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# SQLAlchemy 모델의 Base 클래스
class Base(DeclarativeBase):
    pass
