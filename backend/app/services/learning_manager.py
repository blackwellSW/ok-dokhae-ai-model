"""
learning_manager.py
역할: 규칙 기반 Gate 판정 및 Stage 전이 로직 담당
"""

from typing import Dict, Any, List
from enum import Enum

class Stage(Enum):
    VOCAB = "VOCAB"
    EVIDENCE = "EVIDENCE"
    WHY = "WHY"
    RANDOM = "RANDOM"
    COMPLETE = "COMPLETE"

class LearningManager:
    """
    학습 세션의 현재 상태를 기반으로 다음 단계와 분기를 결정하는 매니저 클래스.
    """

    def __init__(self, session_state: Dict[str, Any]):
        """
        Args:
            session_state: 세션 정보를 포함한 딕셔너리 (current_stage, history 등)
        """
        self.session_state = session_state
        self.stage_order = [Stage.VOCAB, Stage.EVIDENCE, Stage.WHY, Stage.RANDOM]

    def process_student_answer(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        학생의 답변을 받아 Gate를 판단하고 결과를 처리합니다.
        """
        current_stage_str = self.session_state.get("current_stage", Stage.VOCAB.value)
        current_stage = Stage(current_stage_str)
        
        # 1. Gate 판정
        gate_passed = self.check_gate(current_stage, payload)
        
        # 2. 다음 액션 결정
        next_action = self.decide_next_action(current_stage, gate_passed)
        
        return {
            "stage": current_stage.value,
            "gate_passed": gate_passed,
            "next_action": next_action
        }

    def check_gate(self, stage: Stage, payload: Dict[str, Any]) -> bool:
        """
        규칙 기반 Gate 판정 로직
        - VOCAB: answer >= 20자
        - EVIDENCE: answer >= 30자 AND selected_evidence_ids >= 1
        - WHY: answer >= 40자
        - RANDOM: answer >= 20자
        """
        answer = payload.get("answer", "").strip()
        evidence_ids = payload.get("selected_evidence_ids", [])

        if stage == Stage.VOCAB:
            return len(answer) >= 20
        elif stage == Stage.EVIDENCE:
            return len(answer) >= 30 and len(evidence_ids) >= 1
        elif stage == Stage.WHY:
            return len(answer) >= 40
        elif stage == Stage.RANDOM:
            return len(answer) >= 20
        return False

    def decide_next_action(self, stage: Stage, gate_passed: bool) -> Dict[str, Any]:
        """
        판정 결과에 따른 다음 행방 결정
        """
        if gate_passed:
            try:
                idx = self.stage_order.index(stage)
                if idx + 1 < len(self.stage_order):
                    next_stage = self.stage_order[idx + 1]
                    return {
                        "action": "MOVE_NEXT",
                        "new_stage": next_stage.value
                    }
                return {
                    "action": "FINISH_SESSION",
                    "new_stage": Stage.COMPLETE.value
                }
            except ValueError:
                return {"action": "ERROR"}
        
        # 실패 시 힌트 문구 제공 (Branch)
        hints = {
            Stage.VOCAB: "어휘의 사전적 의미보다는 문맥 속에서의 쓰임을 20자 이상으로 더 자세히 설명해보세요.",
            Stage.EVIDENCE: "해당 해석을 뒷받침하는 지문 속 문장을 최소 1개 선택하고, 이유를 30자 이상 작성해야 합니다.",
            Stage.WHY: "작성하신 답변이 논리적으로 타당한지 40자 이상으로 깊이 있게 서술해주세요.",
            Stage.RANDOM: "제시된 심화 질문에 대해 20자 이상의 성의 있는 답변을 남겨주세요."
        }
        return {
            "action": "RETRY",
            "new_stage": stage.value,
            "hint": hints.get(stage, "입력 조건을 다시 확인해주세요.")
        }
