"""
app/db/session.py
역할: FastAPI 핸들러에서 사용할 DB 세션 의존성 제공.
트랜잭션 관리(commit/rollback)는 서비스 레이어에서 담당합니다.
"""
from typing import AsyncGenerator
from .database import async_session_maker

async def get_db() -> AsyncGenerator:
    """FastAPI 핸들러에서 Depends(get_db)로 호출하여 세션을 주입받습니다.
    순수하게 세션만 제공하며 트랜잭션 수명 주기는 호출자가 관리합니다.
    """
    async with async_session_maker() as session:
        yield session
        # session.commit() / rollback() 은 여기서 처리하지 않습니다.
