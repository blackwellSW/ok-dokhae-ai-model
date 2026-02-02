"""
evaluation_controller.py
역할: 외부 평가 엔진(LLM 등)으로부터의 평가 결과를 수신하여 학습 세션 상태를 갱신하는 API 라우터.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.services.study_session_service import (
    StudySessionService, 
    SessionNotFoundError, 
    InvalidTaskError, 
    StageMismatchError
)
from app.repository.session_repository import session_repo

router = APIRouter(prefix="/evaluations", tags=["Evaluations"])

# ------------------------------------------------------------------
# Request / Response Schemas
# ------------------------------------------------------------------

class EvaluationResultRequest(BaseModel):
    """지정된 세션 및 과제에 대한 평가 결과 수신 요청 모델"""
    session_id: str
    task_id: str
    gate_passed: bool


class EvaluationResultResponse(BaseModel):
    """평가 결과 반영 후의 상태 정보를 포함한 응답 모델"""
    status: str
    session_id: str
    task_id: str
    gate_passed: bool
    next_stage_idx: int


# ------------------------------------------------------------------
# API Endpoints
# ------------------------------------------------------------------

@router.post("/result", response_model=EvaluationResultResponse)
async def receive_evaluation_result(request: EvaluationResultRequest):
    """
    외부 평가 엔진으로부터 Gate 통과 여부를 수신하여 세션의 진행 상태를 갱신합니다.
    """
    service = StudySessionService()
    
    try:
        # 1. 서비스 레이어에 평가 결과 반영 위임
        service.apply_evaluation_result(
            session_id=request.session_id,
            task_id=request.task_id,
            gate_passed=request.gate_passed
        )
        
        # 2. 갱신된 세션 정보를 조회하여 응답 데이터 구성
        session = session_repo.get_session(request.session_id)
        if not session:
            # 서비스 레이어 통과 후 세션이 사라지는 경우는 예외 상황
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
                detail="Session synchronization error."
            )
            
        return EvaluationResultResponse(
            status="OK",
            session_id=request.session_id,
            task_id=request.task_id,
            gate_passed=request.gate_passed,
            next_stage_idx=session.get("current_stage_idx", 0)
        )
        
    except SessionNotFoundError as e:
        # 세션 존재하지 않음 (404)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        
    except (InvalidTaskError, StageMismatchError) as e:
        # 현재 순서가 아니거나 잘못된 과제에 대한 평가 시도 (409)
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
        
    except Exception as e:
        # 기타 예상치 못한 서버 내부 오류 (500)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"An unexpected error occurred: {str(e)}"
        )
