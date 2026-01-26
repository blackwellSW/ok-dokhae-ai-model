from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime

# =========================
# 1️⃣ THINKING CONTEXT
# =========================
class Attempt(BaseModel):
    current: int = 1
    max_allowed: int = 3

class Context(BaseModel):
    step_index: int
    step_code: str
    step_name_kr: str
    attempt: Attempt

# =========================
# 2️⃣ USER INPUT TRACE
# =========================
class InputLength(BaseModel):
    chars: int
    tokens: int

class InteractionFlags(BaseModel):
    used_connector_chips: List[str] = []
    copied_from_text: bool = False

class UserInput(BaseModel):
    text: str
    input_type: str = "EXPLANATION"
    length: InputLength
    time_spent_sec: float
    interaction_flags: InteractionFlags

# =========================
# 3️⃣ EVALUATION RESULT
# =========================
class ModelEvalScores(BaseModel):
    qa_score: float
    link_score: float
    length_chars: int
    length_tokens: int
    evidence_refs: int

class ModelEval(BaseModel):
    diag_code: str
    scores: ModelEvalScores

class KeywordGate(BaseModel):
    required: List[str]
    found: List[str]
    missing: List[str]
    passed: bool

class GroundingGate(BaseModel):
    overlap_hits: int
    min_required: int
    passed: bool

class RuleEval(BaseModel):
    keyword_gate: Optional[KeywordGate] = None
    grounding_gate: Optional[GroundingGate] = None

class Evaluation(BaseModel):
    final_status: str  # "PASS", "RETRY"
    label: str         # "WEAK_LINK", "SUCCESS"
    model_eval: ModelEval
    rule_eval: Optional[RuleEval] = None

# =========================
# 4️⃣ SYSTEM FEEDBACK
# =========================
class LogFeedback(BaseModel):
    message_shown: str
    ui_actions: List[str]

# =========================
# 5️⃣ DEBUG / ANALYTICS
# =========================
class DebugInfo(BaseModel):
    evaluator_rule: str
    model_version: str
    notes: Optional[str] = None

# =========================
# META & SESSION
# =========================
class LogMeta(BaseModel):
    log_id: str
    timestamp: datetime
    schema_version: str = "1.0"

class SessionInfo(BaseModel):
    session_id: str
    user_id: str
    passage_id: str
    
# =========================
# ROOT LOG SCHEMA
# =========================
class AnalysisLog(BaseModel):
    meta: LogMeta
    session: SessionInfo
    context: Context
    user_input: UserInput
    evaluation: Evaluation
    feedback: LogFeedback
    debug: Optional[DebugInfo] = None
