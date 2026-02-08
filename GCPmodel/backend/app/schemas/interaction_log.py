"""
app/schemas/interaction_log.py
역할: 상호작용 로그 관련 Pydantic 스키마 정의
"""
from datetime import datetime
from typing import Dict, Any
from pydantic import BaseModel, ConfigDict

class InteractionLogBase(BaseModel):
    session_id: str
    event_type: str
    payload: Dict[str, Any]
    model_config = ConfigDict(from_attributes=True)

class InteractionLogResponse(InteractionLogBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)
