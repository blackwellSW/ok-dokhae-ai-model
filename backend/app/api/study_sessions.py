"""
study_sessions.py
역할: 학습 세션 스테이지 전이 제어 및 제출 관리를 담당하는 API 컨트롤러.
"""

import uuid
from datetime import datetime
from typing import Dict, Any, List
from fastapi import APIRouter, status, HTTPException

from app.models.schemas import (
    SessionCreateRequest,
    SessionCreateResponse,
    TaskOverview,
    TaskDetailResponse,
    SubmissionRequest,
    SubmissionResponse
)
from app.services.learning_manager import LearningManager, Stage
from app.repository.session_repository import session_repo 

router = APIRouter(prefix="/study-sessions", tags=["Study Sessions"])

# ------------------------------------------------------------------
# 도메인 상수 및 템플릿
# ------------------------------------------------------------------

STAGE_ORDER = ["VOCAB", "EVIDENCE", "WHY", "RANDOM"]
COMPLETED_STAGE = "COMPLETED"

STAGE_TEMPLATES = {
    "VOCAB": {
        "question": "가장 핵심적이라고 생각되는 어휘 하나를 골라 문맥적 의미를 설명하세요.",
        "instructions": "어휘를 선택하고 20자 이상의 설명을 작성하세요.",
        "cards": [{"id": "v_1", "content": "어휘 사전 정의", "source": "표준국어대사전"}]
    },
    "EVIDENCE": {
        "question": "방금 설명한 어휘가 주제와 어떤 관련이 있는지 근거 문장을 찾아 연결하세요.",
        "instructions": "근거 문장을 1개 이상 선택하고 30자 이상 서술하세요.",
        "cards": [{"id": "e_1", "content": "지문 핵심 문장 A", "source": "본문"}]
    },
    "WHY": {
        "question": "이 근거가 작가의 주장을 뒷받침하는 결정적인 이유가 무엇일까요?",
        "instructions": "논리적 인과관계를 포함하여 40자 이상 작성하세요.",
        "cards": [{"id": "w_1", "content": "비판적 읽기 가이드", "source": "학습도우미"}]
    },
    "RANDOM": {
        "question": "만약 지문의 상황이 반대로 바뀐다면 어떤 결과가 나타날까요?",
        "instructions": "창의적인 생각을 20자 이상 자유롭게 기술하세요.",
        "cards": [{"id": "r_1", "content": "배경지식 확장 테마", "source": "참조기사"}]
    }
}

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def get_next_stage(current: str) -> str:
    """순차적 Stage 흐름에 따라 다음 Stage를 반환한다."""
    try:
        current_idx = STAGE_ORDER.index(current)
        if current_idx + 1 < len(STAGE_ORDER):
            return STAGE_ORDER[current_idx + 1]
        return COMPLETED_STAGE
    except ValueError:
        return COMPLETED_STAGE

# ------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------

@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(request: SessionCreateRequest):
    """학습 세션을 생성하고 초기 과제 정보를 저장한다."""
    session_id = str(uuid.uuid4())
    
    tasks = [
        TaskOverview(task_id=f"T-{i+1}", stage_type=s, order=i+1)
        for i, s in enumerate(STAGE_ORDER)
    ]

    session_data = {
        "session_id": session_id,
        "work_id": request.work_id,
        "current_stage": STAGE_ORDER[0],
        "tasks": [t.dict() for t in tasks],
        "history": []
    }
    session_repo.create_session(session_id, session_data)
    
    return SessionCreateResponse(session_id=session_id, tasks=tasks)


@router.get("/{session_id}/tasks/{task_id}", response_model=TaskDetailResponse)
async def get_task_detail(session_id: str, task_id: str):
    """현재 진행해야 할 Task 정보를 확인하고 상세 데이터를 반환한다."""
    session = session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 세션 완료 상태 검증 (410 Gone)
    if session.get("current_stage") == COMPLETED_STAGE:
        raise HTTPException(status_code=410, detail="The study session has been completed.")

    # task_id 존재 유무 검증 (400 Bad Request)
    target_task = next((t for t in session.get("tasks", []) if t["task_id"] == task_id), None)
    if not target_task:
        raise HTTPException(status_code=400, detail="Invalid task_id for this session.")

    # 현재 로직 상 진행해야 할 stage와 요청된 task의 stage 일치 유무 검증 (409 Conflict)
    if target_task["stage_type"] != session.get("current_stage"):
        raise HTTPException(
            status_code=409, 
            detail=f"Stage mismatch. Current session stage is {session.get('current_stage')}."
        )

    current_stage = session.get("current_stage")
    template = STAGE_TEMPLATES.get(current_stage, STAGE_TEMPLATES[STAGE_ORDER[0]])

    return TaskDetailResponse(
        stage_type=current_stage,
        question=template["question"],
        evidence_cards=template["cards"],
        instructions=template["instructions"]
    )


@router.post("/{session_id}/tasks/{task_id}/submissions", response_model=SubmissionResponse)
async def submit_answer(session_id: str, task_id: str, submission: SubmissionRequest):
    """제출된 답변의 Gate를 판정하고 결과에 따라 세션의 Stage를 전이시킨다."""
    session = session_repo.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # 세션 완료 상태 검증 (410 Gone)
    current_stage = session.get("current_stage")
    if current_stage == COMPLETED_STAGE:
        raise HTTPException(status_code=410, detail="The study session has been completed.")

    # task_id 및 stage 정합성 검증
    target_task = next((t for t in session.get("tasks", []) if t["task_id"] == task_id), None)
    if not target_task:
        raise HTTPException(status_code=400, detail="Invalid task_id.")
    if target_task["stage_type"] != current_stage:
        raise HTTPException(status_code=409, detail="Submit answer for the current stage task only.")

    # LearningManager에 판정 위임 (Manager는 logic만 처리)
    manager = LearningManager(session)
    payload = submission.dict()
    eval_result = manager.process_student_answer(payload)
    
    gate_passed = eval_result["gate_passed"]
    next_action_data = {}
    new_stage = current_stage

    # Stage 전이 제어 (컨트롤러 책임)
    if gate_passed:
        new_stage = get_next_stage(current_stage)
        if new_stage == COMPLETED_STAGE:
            next_action_data = {
                "type": "SESSION_END",
                "message": "학습이 완료되었습니다.",
                "new_stage": new_stage
            }
        else:
            next_action_data = {
                "type": "MOVE_NEXT",
                "new_stage": new_stage
            }
    else:
        # 실패 시 Branch 유지 및 힌트 제공
        next_action_data = {
            "type": "RETRY",
            "new_stage": current_stage,
            "hint": eval_result["next_action"].get("hint")
        }

    # 제출 이력(history) 확장 저장
    history_entry = {
        "task_id": task_id,
        "stage": current_stage,
        "answer": submission.answer,
        "evidence_ids": submission.selected_evidence_ids,
        "passed": gate_passed,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    update_data = {
        "current_stage": new_stage,
        "history": session.get("history", []) + [history_entry]
    }
    session_repo.update_session(session_id, update_data)

    return SubmissionResponse(
        stage=current_stage,
        gate_passed=gate_passed,
        next_action=next_action_data,
        hint=next_action_data.get("hint")
    )
