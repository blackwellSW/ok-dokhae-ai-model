"""
데이터베이스 초기화 스크립트
역할: 테이블 생성 및 샘플 데이터 추가
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.db.database import Base
from app.db.models import *  # 모든 모델 임포트
from app.core.config import get_settings

settings = get_settings()


async def init_db():
    """데이터베이스 초기화"""
    
    # 엔진 생성
    engine = create_async_engine(
        settings.DATABASE_URL,
        echo=True
    )
    
    # 테이블 생성
    async with engine.begin() as conn:
        # 기존 테이블 삭제 (개발 환경에서만)
        await conn.run_sync(Base.metadata.drop_all)
        # 새 테이블 생성
        await conn.run_sync(Base.metadata.create_all)
    
    print("✅ 데이터베이스 초기화 완료!")
    print(f"📍 DATABASE_URL: {settings.DATABASE_URL}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
