"""
채팅 형식 학습 시스템 API
역할: 복잡한 게이트 시스템 대신 간단한 대화형 학습
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict
# Removed SQLAlchemy imports
# from sqlalchemy.ext.asyncio import AsyncSession

# from app.db.session import get_db
# from app.db.models import User
from app.schemas.user import User
from app.core.auth import get_current_user, get_current_active_student
from app.services.thought_inducer import ThoughtInducer
from app.services.integrated_evaluator import IntegratedEvaluator

router = APIRouter(prefix="/chat", tags=["Chat Learning"])


# ============================================================
# Request/Response Models
# ============================================================

class ChatMessage(BaseModel):
    """채팅 메시지"""
    role: str  # user, assistant
    content: str


class ChatRequest(BaseModel):
    """채팅 요청"""
    work_title: Optional[str] = ""
    context: Optional[str] = ""
    message: str  # 학생의 질문 또는 답변


class ChatResponse(BaseModel):
    """채팅 응답"""
    message: str  # AI의 응답 (사고유도 또는 피드백)
    message_type: str  # question, feedback, encouragement
    evaluation: Optional[Dict] = None  # 평가가 있는 경우


class EvaluateRequest(BaseModel):
    """평가 요청"""
    student_answer: str
    thought_log: Optional[str] = ""


class ConversationHistoryRequest(BaseModel):
    """대화 이력 요청"""
    work_title: str
    limit: int = 10


# ============================================================
# API Endpoints
# ============================================================

@router.post("/send", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_active_student)
):
    """
    채팅 메시지 전송
    
    학생이 질문하거나 답변을 제출하면:
    1. 사고유도 응답 생성 (소크라틱 대화)
    2. 메시지 타입 결정 (질문/피드백/격려)
    3. 응답 반환
    """
    
    try:
        # 사고유도 엔진 사용
        inducer = ThoughtInducer()
        
        result = await inducer.generate_response(
            student_input=request.message,
            work_title=request.work_title,
            context=request.context
        )
        
        # 메시지 타입 결정
        message_type = "question"  # 기본: 질문형
        
        # 사고유도 응답 추출
        induction = result.get("induction", result.get("full_response", ""))
        
        return ChatResponse(
            message=induction,
            message_type=message_type,
            evaluation=None
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"메시지 처리 실패: {str(e)}"
        )


@router.post("/evaluate", response_model=ChatResponse)
async def evaluate_answer(
    request: EvaluateRequest,
    current_user: User = Depends(get_current_active_student)
):
    """
    학생 답변 평가
    
    - 질적 + 정량 평가
    - 개인 맞춤 피드백
    - 점수 및 등급
    """
    
    try:
        # 통합 평가 시스템
        evaluator = IntegratedEvaluator()
        
        result = await evaluator.evaluate_comprehensive(
            student_input=request.student_answer,
            thought_log=request.thought_log
        )
        
        # 피드백 메시지 생성
        feedback_lines = result.get("개인_피드백", [])
        feedback_message = "\n".join(feedback_lines)
        
        # 점수와 등급 추가
        integrated = result.get("통합_평가", {})
        score_message = f"\n\n📊 총점: {integrated.get('총점', 0)}점 (등급: {integrated.get('등급', 'C+')})"
        
        full_message = feedback_message + score_message
        
        return ChatResponse(
            message=full_message,
            message_type="feedback",
            evaluation={
                "qualitative": result.get("질적_평가"),
                "quantitative": result.get("정량_분석"),
                "integrated": result.get("통합_평가")
            }
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"평가 실패: {str(e)}"
        )


@router.get("/works")
async def get_available_works(
    current_user: User = Depends(get_current_active_student)
):
    """
    학습 가능한 작품 목록 조회
    
    TODO: DB에서 실제 작품 데이터 조회
    현재는 샘플 데이터 반환
    """
    
    # 샘플 데이터 (향후 DB 연동)
    works = [
        {
            "work_id": "chunhyang_jeon",
            "title": "춘향전",
            "author": "작자 미상",
            "period": "조선시대",
            "difficulty": 3,
            "genre": "판소리계 소설",
            "description": "신분을 초월한 사랑 이야기"
        },
        {
            "work_id": "honggildongjeon",
            "title": "홍길동전",
            "author": "허균",
            "period": "조선시대",
            "difficulty": 2,
            "genre": "영웅소설",
            "description": "최초의 한글 소설, 서얼 차별에 저항하는 홍길동의 이야기"
        },
        {
            "work_id": "kuunmong",
            "title": "구운몽",
            "author": "김만중",
            "period": "조선시대",
            "difficulty": 4,
            "genre": "몽자류 소설",
            "description": "꿈과 현실, 불교와 유교의 조화"
        }
    ]
    
    return {"works": works}


@router.get("/health")
async def chat_health():
    """채팅 시스템 헬스 체크"""
    return {
        "status": "healthy",
        "features": [
            "Socratic Dialogue",
            "Real-time Evaluation",
            "Personalized Feedback"
        ]
    }
