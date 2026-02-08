
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class LearningStateBase(BaseModel):
    state_id: str
    user_id: str
    current_work_id: Optional[str] = None
    current_chunk_id: Optional[str] = None
    current_stage_id: Optional[str] = None
    session_id: Optional[str] = None
    status: str = "ACTIVE"
    current_turn: int = 1
    max_turns: int = 4
    checkpoint_data: Dict = {}
    last_question: Optional[str] = None
    last_answer: Optional[str] = None
    total_stages_completed: int = 0
    total_time_spent: int = 0
    weak_skills: Dict = {}

class LearningStateCreate(LearningStateBase):
    pass

class LearningState(LearningStateBase):
    created_at: str
    updated_at: str

class ThinkingLogBase(BaseModel):
    log_id: str
    state_id: str
    stage_id: str
    question: str
    answer: str
    eval_result: Dict = {}
    strategy_used: str
    time_spent: int
    thinking_pattern: Dict = {}
    skill_demonstrated: List = []
    error_type: Optional[str] = None

class ThinkingLogCreate(ThinkingLogBase):
    pass

class ThinkingLog(ThinkingLogBase):
    created_at: str

class TeacherDashboardData(BaseModel):
    dashboard_id: str
    teacher_id: str
    class_id: Optional[str] = None
    student_progress: Dict = {}
    stage_failure_rate: Dict = {}
    question_pass_rate: Dict = {}
    active_sessions: int = 0
    students_needing_help: List = []
    updated_at: str
