"""
리포트 생성/조회 API
역할: 학습 리포트 생성, 저장, 조회

📋 프론트엔드 개발자를 위한 사용 가이드
==========================================

1. 리포트 생성: POST /reports/generate
   - 평가 결과를 입력받아 리포트 JSON 반환

2. 리포트 조회: GET /reports/{report_id}
   - 저장된 리포트 재조회 (학생 기록 화면용)

3. 리포트 목록: GET /reports
   - 내 리포트 목록 조회
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
# Removed SQLAlchemy imports
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select, desc
import uuid

# from app.db.session import get_db
# from app.db.models import User, LearningReport
from app.schemas.user import User
from app.core.auth import get_current_user
from app.services.report_generator import ReportGenerator
from app.repository.report_repository import report_repo

router = APIRouter(prefix="/reports", tags=["📊 Report Management"])


# ============================================================
# Request/Response Models
# ============================================================

class Citation(BaseModel):
    """근거(인용) 정보"""
    quote: str = Field(..., description="인용 문장")
    document_id: Optional[str] = Field(None, description="문서 ID")
    anchor: Dict[str, Any] = Field(
        default_factory=dict, 
        description="위치 정보: {page, paragraph, char_start, char_end}"
    )
    confidence: float = Field(1.0, description="신뢰도 (0.0 ~ 1.0)")


class ReportRequest(BaseModel):
    """리포트 생성 요청 데이터"""
    session_id: Optional[str] = Field(None, description="연결할 세션 ID")
    qualitative_eval: Dict[str, Any] = Field(..., description="질적 평가 결과")
    quantitative_eval: Dict[str, Any] = Field(..., description="정량 평가 결과")
    integrated_eval: Dict[str, Any] = Field(..., description="통합 평가 결과")
    thought_log: List[Dict[str, Any]] = Field(default_factory=list, description="사고 과정 로그")


class ScoreItem(BaseModel):
    """점수 항목"""
    label: str = Field(..., description="항목 라벨 (영문)")
    score: float = Field(..., description="점수 (0-10)")
    label_text: str = Field(..., description="항목 라벨 (한글)")
    reason: str = Field(..., description="평가 근거")
    citations: List[Citation] = Field(default_factory=list, description="근거 인용")


class FlowItem(BaseModel):
    """사고 흐름 분석 항목"""
    step: str = Field(..., description="단계명")
    status: str = Field(..., description="상태: perfect | good | weak")
    comment: str = Field(..., description="교사 코멘트")
    quote: Optional[str] = Field(None, description="학생 답변 인용")


class ReportResponse(BaseModel):
    """리포트 응답 데이터"""
    report_id: str = Field(..., description="리포트 고유 ID")
    session_id: Optional[str] = Field(None, description="연결된 세션 ID")
    summary: str = Field(..., description="전체 요약")
    tags: List[str] = Field(default_factory=list, description="학습 태그")
    scores: List[ScoreItem] = Field(default_factory=list, description="상세 점수")
    flow_analysis: List[FlowItem] = Field(default_factory=list, description="사고 흐름 분석")
    prescription: str = Field(..., description="개선 처방")
    total_score: float = Field(0, description="총점")
    grade: str = Field("C+", description="등급")
    created_at: str = Field(..., description="생성 시각")


class ReportListItem(BaseModel):
    """리포트 목록 항목"""
    report_id: str
    session_id: Optional[str]
    summary: str
    total_score: float
    grade: str
    created_at: str


# ============================================================
# API Endpoints
# ============================================================

@router.post(
    "/generate",
    response_model=ReportResponse,
    summary="📝 리포트 생성",
    description="학습 리포트를 생성하고 저장합니다."
)
async def generate_report(
    request: ReportRequest,
    current_user: User = Depends(get_current_user)
):
    """학습 리포트 생성 및 저장"""
    
    try:
        generator = ReportGenerator()
        
        report_data = generator.generate(
            qualitative_eval=request.qualitative_eval,
            quantitative_eval=request.quantitative_eval,
            integrated_eval=request.integrated_eval,
            thought_log=request.thought_log
        )
        
        # 리포트 ID 생성
        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        created_at = datetime.utcnow().isoformat()
        
        # 통합 평가에서 점수/등급 추출
        total_score = request.integrated_eval.get("총점", 0)
        grade = request.integrated_eval.get("등급", "C+")
        
        # Firestore 저장용 Dictionary
        report_dict = {
            "report_id": report_id,
            "session_id": request.session_id,
            "user_id": current_user.user_id,
            "report_type": "student", # Added field
            "summary": report_data.get("summary", ""),
            "tags": report_data.get("tags", []),
            "scores": report_data.get("scores", []),
            "flow_analysis": report_data.get("flow_analysis", []),
            "prescription": report_data.get("prescription", ""),
            "total_score": total_score,
            "grade": grade,
            "created_at": created_at,
            "raw_data": {
                "qualitative": request.qualitative_eval,
                "quantitative": request.quantitative_eval,
                "integrated": request.integrated_eval
            }
        }
        
        # Save to Firestore
        await report_repo.create_report(report_dict)
        
        return ReportResponse(
            report_id=report_id,
            session_id=request.session_id,
            summary=report_data.get("summary", "학습이 완료되었습니다."),
            tags=report_data.get("tags", []),
            scores=report_data.get("scores", []),
            flow_analysis=report_data.get("flow_analysis", []),
            prescription=report_data.get("prescription", "다음 학습을 진행해보세요."),
            total_score=total_score,
            grade=grade,
            created_at=created_at
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"리포트 생성 실패: {str(e)}"
        )


@router.get(
    "/{report_id}",
    response_model=ReportResponse,
    summary="📖 리포트 조회",
    description="저장된 리포트를 조회합니다."
)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user)
):
    """리포트 조회"""
    
    report_data = await report_repo.get_report(report_id)
    
    if not report_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"리포트를 찾을 수 없습니다: {report_id}"
        )
    
    # Ownership check can be added here if needed
    if report_data.get("user_id") != current_user.user_id:
        # Check if user is teacher/admin? For now, allow simple ownership
        pass 
        
    return ReportResponse(
        report_id=report_data["report_id"],
        session_id=report_data.get("session_id"),
        summary=report_data.get("summary", ""),
        tags=report_data.get("tags", []),
        scores=report_data.get("scores", []),
        flow_analysis=report_data.get("flow_analysis", []),
        prescription=report_data.get("prescription", ""),
        total_score=report_data.get("total_score", 0),
        grade=report_data.get("grade", "C+"),
        created_at=report_data.get("created_at", "")
    )


@router.get(
    "",
    summary="📚 내 리포트 목록",
    description="현재 사용자의 리포트 목록을 조회합니다."
)
async def list_reports(
    days: int = Query(30, description="최근 N일 이내"),
    current_user: User = Depends(get_current_user)
):
    """내 리포트 목록 조회"""
    
    reports = await report_repo.get_reports_by_user(current_user.user_id, days=days)
    
    report_list = []
    for r in reports:
        summary_text = r.get("summary", "")
        if len(summary_text) > 50:
            summary_text = summary_text[:50] + "..."
            
        report_list.append(ReportListItem(
            report_id=r["report_id"],
            session_id=r.get("session_id"),
            summary=summary_text,
            total_score=r.get("total_score", 0),
            grade=r.get("grade", "C+"),
            created_at=r.get("created_at", "")
        ))
    
    return {
        "reports": report_list,
        "total": len(report_list)
    }
