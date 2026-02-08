"""
app/api/classical_literature.py
역할: 고전문학 학습 및 평가 API 엔드포인트
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional, Dict

from app.services.thought_inducer import ThoughtInducer
from app.services.integrated_evaluator import IntegratedEvaluator

router = APIRouter(prefix="/classical-literature", tags=["Classical Literature AI"])

# ============================================================
# Request/Response Models
# ============================================================

class ThoughtInductionRequest(BaseModel):
    """사고유도 대화 요청"""
    student_input: str
    work_title: Optional[str] = ""
    context: Optional[str] = ""


class ThoughtInductionResponse(BaseModel):
    """사고유도 대화 응답"""
    induction: str  # [사고유도] 응답
    log: str  # [사고로그] 내용
    full_response: str


class EvaluationRequest(BaseModel):
    """학생 답변 평가 요청"""
    student_input: str
    thought_log: Optional[str] = ""


class EvaluationResponse(BaseModel):
    """종합 평가 응답"""
    qualitative_eval: Dict  # 질적 평가
    quantitative_analysis: Dict  # 정량 분석
    integrated_score: Dict  # 통합 점수
    feedback: List[str]  # 개인 맞춤 피드백


class QuickEvaluationRequest(BaseModel):
    """간단 평가 요청"""
    student_input: str


# ============================================================
# API Endpoints
# ============================================================

@router.post("/dialogue", response_model=ThoughtInductionResponse)
async def generate_thought_induction(request: ThoughtInductionRequest):
    """
    학생 질문에 대한 사고유도 대화 생성
    
    소크라틱 대화법을 활용하여 학생이 스스로 생각하도록 유도하는
    응답을 생성하고, 예상되는 사고 과정을 로깅합니다.
    """
    try:
        inducer = ThoughtInducer()
        result = await inducer.generate_response(
            student_input=request.student_input,
            work_title=request.work_title,
            context=request.context
        )
        
        return ThoughtInductionResponse(
            induction=result["induction"],
            log=result["log"],
            full_response=result["full_response"]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"사고유도 생성 실패: {str(e)}"
        )


@router.post("/evaluate", response_model=EvaluationResponse)
async def evaluate_student_response(request: EvaluationRequest):
    """
    학생 답변에 대한 종합 평가
    
    Gemini 기반 질적 평가 (70%)와 언어 분석 기반 정량 평가 (30%)를
    통합하여 종합 점수와 개인 맞춤 피드백을 제공합니다.
    
    평가 차원:
    - 질적: 추론 깊이, 비판적 사고, 문학적 이해
    - 정량: 어휘 다양성, 핵심 개념어, 문장 복잡도, 반복 패턴, 감정 톤
    """
    try:
        evaluator = IntegratedEvaluator()
        result = await evaluator.evaluate_comprehensive(
            student_input=request.student_input,
            thought_log=request.thought_log
        )
        
        return EvaluationResponse(
            qualitative_eval=result["질적_평가"],
            quantitative_analysis=result["정량_분석"],
            integrated_score=result["통합_평가"],
            feedback=result["개인_피드백"]
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"평가 실패: {str(e)}"
        )


@router.post("/quick-evaluate")
async def quick_evaluate(request: QuickEvaluationRequest):
    """
    학생 답변에 대한 빠른 평가 (사고로그 없이)
    
    간단한 피드백이 필요할 때 사용합니다.
    """
    try:
        evaluator = IntegratedEvaluator()
        result = await evaluator.quick_evaluate(request.student_input)
        
        return {
            "integrated_score": result["통합_평가"],
            "feedback": result["개인_피드백"]
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"빠른 평가 실패: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """API 헬스 체크"""
    return {
        "status": "healthy",
        "service": "Classical Literature AI",
        "features": [
            "Socratic Dialogue Generation",
            "Qualitative Evaluation (Gemini)",
            "Quantitative Language Analysis",
            "Integrated Assessment (70% + 30%)",
            "Personalized Feedback"
        ]
    }
