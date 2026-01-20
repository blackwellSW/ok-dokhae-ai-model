import sys
import os
from typing import Dict, List

# 패키지 경로를 추가하여 어디서든 실행 가능하게 함
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.logic.analyzer import LogicAnalyzer
from backend.logic.evaluator import Evaluator
from backend.logic.session import SessionManager

class OkDokHaeCore:
    """
    옥독해의 핵심 파이프라인을 관리하는 통합 클래스입니다.
    웹 서버(FastAPI) 없이 로직만 수행합니다.
    """
    def __init__(self):
        self.analyzer = LogicAnalyzer()
        self.evaluator = Evaluator()
        self.session_manager = SessionManager()
    
    def start_session(self, passage_text: str) -> Dict:
        analysis = self.analyzer.analyze(passage_text)

        session_id = self.session_manager.create_session(
            passage_text=passage_text,
            analyzer_output={
                "claim_candidates": analysis["claim_candidates"],
                "evidence_candidates": analysis["evidence_candidates"]
            }
        )

        return {
            "session_id": session_id,
            "stage": "claim",
            "claim_candidates": analysis["claim_candidates"],
            "sentences": analysis["sentences"]
        }
    
    def submit_claim(self, session_id: str, claim_text: str) -> Dict:
        self.session_manager.submit_claim(session_id, claim_text)

        return {
            "session_id": session_id,
            "stage": "evidence",
            "evidence_candidates": self.session_manager
                .get_session(session_id)
                .evidence_candidates
        }
    
    def submit_evidence(self, session_id: str, evidence_ids: List[int]) -> Dict:
        self.session_manager.submit_evidence(session_id, evidence_ids)

        return {
            "session_id": session_id,
            "stage": "reasoning",
            "message": "선택한 근거로 주장을 어떻게 뒷받침하는지 설명해보세요."
        }

    def submit_reasoning(self, session_id: str, reasoning_text: str) -> Dict:
        session = self.session_manager.get_session(session_id)

        result = self.evaluator.validate_reasoning(
            question="선택한 근거로 주장을 설명하시오.",
            claim_text=session.claim_text,
            evidence_texts=[
                session.evidence_candidates[i]["text"]
                for i in session.selected_evidence_ids
            ],
            reasoning_text=reasoning_text
        )

        self.session_manager.submit_reasoning(
            session_id=session_id,
            reasoning_text=reasoning_text,
            validation_result=result
        )
        return {
            "session_id": session_id,
            "stage": "done",
            "label": result["label"],
            "scores": result["scores"]
        }

if __name__ == "__main__":
    # 간단한 터미널 실행 예시
    core = OkDokHaeCore()

    passage = "산업혁명은 생산 방식의 변화를 통해 사회 구조 전반에 큰 영향을 미쳤다."

    # 1. 세션 시작
    start = core.start_session(passage)
    session_id = start["session_id"]
    print("[START]", start)

    # 2. 주장 제출
    claim = "산업혁명은 사회 구조를 크게 변화시켰다."
    res_claim = core.submit_claim(session_id, claim)
    print("[CLAIM]", res_claim)

    # 3. 근거 선택 (첫 번째 근거를 선택했다고 가정)
    res_evidence = core.submit_evidence(session_id, [0])
    print("[EVIDENCE]", res_evidence)

    # 4. 연결 설명 제출 (Validation 실행)
    reasoning = "기계화된 생산 방식이 확산되면서 노동 구조와 계층 구성이 달라졌기 때문이다."
    res_reasoning = core.submit_reasoning(session_id, reasoning)
    print("[REASONING]", res_reasoning)