"""
app/schemas/study_session.py
역할: 학습 세션 및 평가 결과 Pydantic 스키마 정의
"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, ConfigDict, Field

class TaskOverview(BaseModel):
    task_id: str
    stage_type: str
    order: int
    status: str = "PENDING"
    
    model_config = ConfigDict(from_attributes=True)

class SessionCreateRequest(BaseModel):
    work_id: str
    selected_chunk_ids: List[str]

class SessionCreateResponse(BaseModel):
    session_id: str
    tasks: List[TaskOverview]
    
    model_config = ConfigDict(from_attributes=True)

class SubmissionRequest(BaseModel):
    answer: str
    selected_evidence_ids: List[str] = Field(default_factory=list)

class SubmissionResponse(BaseModel):
    stage: str
    gate_passed: bool
    next_action: Dict[str, Any]
    hint: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)

class EvaluationResultCreate(BaseModel):
    session_id: str
    task_id: str
    gate_passed: bool
    evaluator_type: str = "LLM" # LLM, HUMAN, RULE
    score: Optional[float] = None
    feedback: Optional[str] = None
