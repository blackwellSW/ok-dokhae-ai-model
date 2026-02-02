"""
study_session_service.py
역할: 학습 세션의 생명주기 및 상태 전이를 관리하는 서비스 레이어.
익셉션 처리 및 current_stage_idx 기반의 흐름 제어를 담당합니다.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.models.schemas import (
    SessionCreateRequest,
    SessionCreateResponse,
    TaskOverview,
    SubmissionRequest,
    SubmissionResponse
)
from app.repository.session_repository import session_repo


# ------------------------------------------------------------------
# 도메인 예외 클래스 정의
# ------------------------------------------------------------------

class StudySessionError(Exception):
    """학습 세션 서비스의 기본 예외 클래스"""
    pass

class SessionNotFoundError(StudySessionError):
    """세션을 찾을 수 없는 경우 발생"""
    pass

class InvalidTaskError(StudySessionError):
    """요청된 Task가 세션에 존재하지 않거나 현재 순서와 맞지 않는 경우 발생"""
    pass

class StageMismatchError(StudySessionError):
    """현재 순서가 아닌 Task에 접근하려 할 때 발생"""
    pass


# ------------------------------------------------------------------
# StudySessionService 구현
# ------------------------------------------------------------------

class StudySessionService:
    """
    학습 세션 상태 제어 및 비즈니스 로직을 처리하는 핵심 서비스.
    """

    def create_session(self, request: SessionCreateRequest) -> SessionCreateResponse:
        """
        새로운 학습 세션을 생성하고 초기 상태를 Firestore에 저장합니다.
        """
        session_id = str(uuid.uuid4())
        
        tasks: List[Dict[str, Any]] = []
        task_overviews: List[TaskOverview] = []
        
        order = 1
        # QUESTION -> EVIDENCE -> ANSWER 흐름 구성
        for chunk_id in request.selected_chunk_ids:
            for stage in ["QUESTION", "EVIDENCE", "ANSWER"]:
                task_id = str(uuid.uuid4())
                task_data = {
                    "task_id": task_id,
                    "chunk_id": chunk_id,
                    "stage_type": stage,
                    "order": order,
                    "status": "PENDING"
                }
                tasks.append(task_data)
                task_overviews.append(
                    TaskOverview(task_id=task_id, stage_type=stage, order=order)
                )
                order += 1

        session_data = {
            "session_id": session_id,
            "work_id": request.work_id,
            "status": "CREATED",
            "current_stage_idx": 0,
            "tasks": tasks,
            "history": [],
            "created_at": datetime.utcnow().isoformat()
        }

        session_repo.create_session(session_id, session_data)

        return SessionCreateResponse(
            session_id=session_id,
            tasks=task_overviews
        )

    def get_task_detail(self, session_id: str, task_id: str) -> Dict[str, Any]:
        """
        현재 진행 순서에 맞는 Task의 상세 정보를 반환합니다.
        """
        session = session_repo.get_session(session_id)
        if not session:
            raise SessionNotFoundError(f"Session {session_id} not found.")

        current_idx = session.get("current_stage_idx", 0)
        tasks = session.get("tasks", [])

        if current_idx >= len(tasks):
            raise StageMismatchError("All tasks in this session have been completed.")

        current_task = tasks[current_idx]
        if current_task["task_id"] != task_id:
            raise StageMismatchError(
                f"Task ID mismatch. Current expected task is {current_task['task_id']}."
            )

        stage_type = current_task["stage_type"]
        
        return {
            "stage_type": stage_type,
            "question": self._get_base_question(stage_type),
            "evidence_cards": self._get_context_evidence(session.get("work_id")),
            "instructions": self._get_instructions(stage_type),
            "status": current_task["status"]
        }

    def submit_answer(self, session_id: str, task_id: str, request: SubmissionRequest) -> SubmissionResponse:
        """
        학생의 답변을 제출받고 Task 상태를 SUBMITTED로 변경합니다.
        """
        session = session_repo.get_session(session_id)
        if not session:
            raise SessionNotFoundError(f"Session {session_id} not found.")

        current_idx = session.get("current_stage_idx", 0)
        tasks = session.get("tasks", [])

        if current_idx >= len(tasks) or tasks[current_idx]["task_id"] != task_id:
            raise StageMismatchError("You can only submit for the current active task.")

        # Task 상태 업데이트: SUBMITTED
        tasks[current_idx]["status"] = "SUBMITTED"

        # 로그(history) 기록
        history_entry = {
            "task_id": task_id,
            "stage": tasks[current_idx]["stage_type"],
            "answer": request.answer,
            "selected_evidence_ids": request.selected_evidence_ids,
            "submitted_at": datetime.utcnow().isoformat()
        }

        update_data = {
            "tasks": tasks,
            "history": session.get("history", []) + [history_entry],
            "updated_at": datetime.utcnow().isoformat()
        }
        
        session_repo.update_session(session_id, update_data)

        return SubmissionResponse(
            stage=tasks[current_idx]["stage_type"],
            gate_passed=False,
            next_action={
                "type": "WAIT_FOR_EVAL",
                "message": "AI 채점 결과를 기다리는 중입니다."
            },
            hint=None
        )

    def apply_evaluation_result(self, session_id: str, task_id: str, gate_passed: bool):
        """
        외부 평가 결과(Gate)를 세션 상태에 반영합니다.
        통과 시 인덱스를 증가시키고, 실패 시 현재 인덱스를 유지합니다.
        """
        session = session_repo.get_session(session_id)
        if not session:
            raise SessionNotFoundError(f"Session with ID {session_id} not found.")

        current_idx = session.get("current_stage_idx", 0)
        tasks = session.get("tasks", [])

        # 1. 인덱스 범위 확인 (초과 방어)
        if current_idx >= len(tasks):
            raise InvalidTaskError("All tasks in this session are already processed.")

        # 2. current_stage_idx에 해당하는 task_id 검증
        if tasks[current_idx]["task_id"] != task_id:
            raise InvalidTaskError(
                f"Task ID mismatch. Expected current task ID: {tasks[current_idx]['task_id']}"
            )

        # 3 & 4. gate_passed 여부에 따른 인덱스 전이 로직
        new_idx = current_idx
        if gate_passed:
            tasks[current_idx]["status"] = "PASSED"
            new_idx = current_idx + 1
        else:
            tasks[current_idx]["status"] = "FAILED"
            # gate_passed가 False면 new_idx = current_idx (유지)

        # 5. index가 tasks 길이를 초과하지 않도록 방칭
        if new_idx > len(tasks):
            new_idx = len(tasks)

        # 6. 변경된 세션 상태를 repository에 저장
        updated_session = {
            "tasks": tasks,
            "current_stage_idx": new_idx,
            "updated_at": datetime.utcnow().isoformat()
        }

        # 모든 태스크가 완료된 경우 세션 상태 업데이트 (선택 사항)
        if new_idx >= len(tasks):
            updated_session["status"] = "COMPLETED"

        session_repo.update_session(session_id, updated_session)

    # --- Private Helpers ---

    def _get_base_question(self, stage: str) -> str:
        templates = {
            "QUESTION": "본문에 제시된 핵심 내용을 질문에 맞게 요약하세요.",
            "EVIDENCE": "당신의 답변을 증명할 수 있는 문장을 지문에서 선택하세요.",
            "ANSWER": "선택한 근거를 논리적으로 연결하여 답변을 완성하세요."
        }
        return templates.get(stage, "질문 내용을 불러올 수 없습니다.")

    def _get_instructions(self, stage: str) -> str:
        instructions = {
            "QUESTION": "핵심 내용을 문장 형태로 20자 이상 작성하세요.",
            "EVIDENCE": "근거 카드를 1개 이상 선택하고 이유를 작성하세요.",
            "ANSWER": "완결된 문장 구조로 논리적인 결론을 도출하세요."
        }
        return instructions.get(stage, "안내에 따라 답변을 작성해 주세요.")

    def _get_context_evidence(self, work_id: Optional[str]) -> List[Dict[str, Any]]:
        return [
            {"id": "ev_ref_01", "content": "지문 분석 데이터의 일부입니다.", "source": "original_text"}
        ]
