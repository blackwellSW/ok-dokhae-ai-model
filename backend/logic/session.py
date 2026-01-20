from typing import List, Dict, Optional
from dataclasses import dataclass, field
import time
import uuid

@dataclass
class SessionState:
    session_id: str
    passage_text: str

    # 단계 상태 - claim, evidence, reasoning, done
    stage: str

    # 학생 입력
    claim_text: Optional[str] = None
    selected_evidence_ids: List[int] = field(default_factory=list)
    reasoning_text: Optional[str] = None

    # 분석 결과 (analyzer 결과 캐시)
    claim_candidates: List[Dict] = field(default_factory=list)
    evidence_candidates: List[Dict] = field(default_factory=list)

    # Validation 결과
    validation_label: Optional[str] = None
    validation_scores: Dict = field(default_factory=dict)

    # 로그
    timestamps: Dict[str, float] = field(default_factory=dict)

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}

    def create_session(self, passage_text: str, analyzer_output: Dict) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = SessionState(
            session_id=session_id,
            passage_text=passage_text,
            stage="claim",
            claim_candidates=analyzer_output["claim_candidates"],
            evidence_candidates=analyzer_output["evidence_candidates"],
            timestamps={"start": time.time()}
        )
        return session_id

    def get_session(self, session_id: str) -> SessionState:
        return self.sessions[session_id]

    def submit_claim(self, session_id: str, claim_text: str):
        s = self.sessions[session_id]
        assert s.stage == "claim"

        s.claim_text = claim_text
        s.timestamps["claim"] = time.time()
        s.stage = "evidence"
    
    def submit_evidence(self, session_id: str, evidence_ids: List[int]):
        s = self.sessions[session_id]
        assert s.stage == "evidence"

        s.selected_evidence_ids = evidence_ids
        s.timestamps["evidence"] = time.time()
        s.stage = "reasoning"
    
    def submit_reasoning(
        self,
        session_id: str,
        reasoning_text: str,
        validation_result: Dict
    ):
        s = self.sessions[session_id]
        assert s.stage == "reasoning"

        s.reasoning_text = reasoning_text
        s.timestamps["reasoning"] = time.time()

        s.validation_label = validation_result["label"]
        s.validation_scores = validation_result["scores"]
        s.stage = "done"