"""
완전한 학습 시스템 API
역할: Thinking Path 기반 학습 흐름 제어
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services.learning_state_manager import LearningStateManager
from app.services.thinking_path_engine import ThinkingPathEngine
from app.services.strategy_manager import StrategyManager
from app.services.learning_analyzer import LearningAnalyzer
from app.services.content_manager import ContentManager
from app.services.anomaly_detector import AnomalyDetector

router = APIRouter(prefix="/learning", tags=["Learning System"])


# ============================================================
# Request/Response Models
# ============================================================

class StartLearningRequest(BaseModel):
    """학습 시작 요청"""
    user_id: str
    work_id: str
    chunk_id: str


class StartLearningResponse(BaseModel):
    """학습 시작 응답"""
    state_id: str
    resumed: bool
    current_stage_id: str
    first_question: str


class SubmitAnswerRequest(BaseModel):
    """답변 제출 요청"""
    state_id: str
    stage_id: str
    question: str
    answer: str
    time_spent: int  # 초


class SubmitAnswerResponse(BaseModel):
    """답변 제출 응답"""
    passed: bool
    action: str  # pass, retry, hint, strategy_change
    feedback: str
    hint: Optional[str] = None
    next_question: Optional[str] = None
    next_stage_id: Optional[str] = None
    anomalies: List[Dict] = []
    
    # 세션 상태 정보
    session_status: str = "ACTIVE"
    current_turn: int
    report_id: Optional[str] = None


class StudentReportRequest(BaseModel):
    """학생 리포트 요청"""
    user_id: str
    days: int = 7


# ============================================================
# API Endpoints
# ============================================================

@router.post("/start", response_model=StartLearningResponse)
async def start_learning(
    request: StartLearningRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    학습 시작 또는 재개
    
    - 새로운 학습 시작
    - 중단된 학습 복구
    """
    try:
        # 학습 상태 생성/복구
        state_manager = LearningStateManager(db)
        state_data = await state_manager.create_or_resume_state(
            user_id=request.user_id,
            work_id=request.work_id,
            chunk_id=request.chunk_id
        )
        
        # 첫 질문 생성
        thinking_engine = ThinkingPathEngine(db)
        first_question = await thinking_engine.generate_dynamic_question(
            state_id=state_data["state_id"],
            stage_id=state_data["current_stage_id"],
            context={
                "work_id": request.work_id,
                "chunk_id": request.chunk_id
            }
        )
        
        return StartLearningResponse(
            state_id=state_data["state_id"],
            resumed=state_data["resumed"],
            current_stage_id=state_data["current_stage_id"],
            first_question=first_question
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"학습 시작 실패: {str(e)}"
        )


@router.post("/submit-answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    request: SubmitAnswerRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    답변 제출 및 평가 (4회 핑퐁 후 종료)
    """
    try:
        state_manager = LearningStateManager(db)
        
        # 1. 답변 평가 및 게이트 판단
        thinking_engine = ThinkingPathEngine(db)
        # TODO: 실제 구현에서는 anomaly checks 등 포함
        
        eval_result = await thinking_engine.evaluate_and_gate(
            state_id=request.state_id,
            stage_id=request.stage_id,
            question=request.question,
            answer=request.answer,
            time_spent=request.time_spent
        )

        # 2. 턴 증가 및 세션 종료 확인
        turn_info = await state_manager.increment_turn(request.state_id)
        current_turn = turn_info["current_turn"]
        is_completed = turn_info["is_completed"]
        
        next_question = None
        report_id = None
        session_status = "ACTIVE"
        
        # 3. 종료 시 로직 (4회 응답 완료)
        if is_completed:
            session_status = "COMPLETED"
            
            # 리포트 생성
            # TODO: user_id는 state 조회해서 가져와야 함 (임시로 request나 state에서 조회한다고 가정)
            # 여기서는 편의상 "temp_user" 사용 또는 state 조회 로직 추가 필요
            # 실제로는 get_current_user 의존성을 사용하는 것이 좋음
            
            analyzer = LearningAnalyzer(db)
            report_result = await analyzer.generate_session_report(
                user_id="temp_user_id", # 실제로는 DB의 learning_state.user_id 사용 권장
                state_id=request.state_id
            )
            report_id = report_result["report_id"]
            
        else:
            # 4. 진행 시 다음 질문 생성 logic (기존 로직 유지/보완)
            if eval_result["action"] == "pass" and eval_result.get("next_stage_id"):
                 next_question = await thinking_engine.generate_dynamic_question(
                    state_id=request.state_id,
                    stage_id=eval_result["next_stage_id"],
                    context={"work_id": "work_id", "chunk_id": "chunk_id"} 
                )
                 await state_manager.update_state(
                    request.state_id, 
                    {"current_stage_id": eval_result["next_stage_id"]}
                )
            elif eval_result["action"] in ["retry", "hint"]:
                strategy_manager = StrategyManager(db)
                weak_skills = await state_manager.get_weak_skills(request.state_id)
                selected_strategy = await strategy_manager.select_strategy(
                    state_id=request.state_id,
                    recent_failures=[{"fail_reason": eval_result.get("fail_reason")}],
                    current_weak_skills=weak_skills
                )
                # 재시도 질문
                next_question = await thinking_engine.generate_dynamic_question(
                    state_id=request.state_id,
                    stage_id=request.stage_id,
                    context={}
                )

        return SubmitAnswerResponse(
            passed=eval_result["passed"],
            action=eval_result["action"],
            feedback=eval_result["feedback"],
            hint=eval_result.get("hint"),
            next_question=next_question,
            next_stage_id=eval_result.get("next_stage_id"),
            anomalies=[],
            session_status=session_status,
            current_turn=current_turn,
            report_id=report_id
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"답변 처리 실패: {str(e)}"
        )


@router.post("/student-report")
async def get_student_report(
    request: StudentReportRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    학생용 학습 리포트 조회
    
    - 막힌 지점
    - 약한 사고 유형
    - 개선 영역
    """
    try:
        analyzer = LearningAnalyzer(db)
        report = await analyzer.generate_student_report(
            user_id=request.user_id,
            days=request.days
        )
        
        return report
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"리포트 생성 실패: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """시스템 헬스 체크"""
    return {
        "status": "healthy",
        "features": [
            "Thinking Path Engine",
            "Dynamic Question Generation",
            "Gate Passing Logic",
            "Strategy Adaptation",
            "Anomaly Detection",
            "Learning Analytics"
        ]
    }
