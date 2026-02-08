"""
schemas.py
역할: API 요청 및 응답에서 사용되는 공통 Pydantic 데이터 모델 정의
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


# ------------------------------------------------------------------
# Request Models
# ------------------------------------------------------------------

class SessionCreateRequest(BaseModel):
    """학습 세션 생성을 위한 요청 모델"""
    work_id: str
    selected_chunk_ids: List[str]


class SubmissionRequest(BaseModel):
    """학생 답변 제출을 위한 요청 모델"""
    answer: str
    selected_evidence_ids: Optional[List[str]] = Field(default_factory=list)


# ------------------------------------------------------------------
# Shared / Nested Models
# ------------------------------------------------------------------

class TaskOverview(BaseModel):
    """세션 내 과제 요약 정보"""
    task_id: str
    stage_type: str
    order: int


# ------------------------------------------------------------------
# Response Models
# ------------------------------------------------------------------

class SessionCreateResponse(BaseModel):
    """학습 세션 생성 응답 모델"""
    session_id: str
    tasks: List[TaskOverview]


class TaskDetailResponse(BaseModel):
    """과제 상세 정보 조회를 위한 응답 모델"""
    stage_type: str
    question: str
    evidence_cards: List[Dict[str, Any]]
    instructions: str


class SubmissionResponse(BaseModel):
    """답변 제출 결과 및 다음 행동을 포함한 응답 모델"""
    stage: str
    gate_passed: bool
    next_action: Dict[str, Any]
    hint: Optional[str] = None
