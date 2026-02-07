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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta
import uuid

from app.db.session import get_db
from app.db.models import User, LearningReport
from app.core.auth import get_current_user
from app.services.report_generator import ReportGenerator

router = APIRouter(prefix="/reports", tags=["📊 Report Management"])


# ============================================================
# Request/Response Models
# ============================================================

class Citation(BaseModel):
    """
    근거(인용) 정보 - 표준 스키마
    
    모든 평가/피드백에서 공통 사용
    """
    quote: str = Field(..., description="인용 문장")
    document_id: Optional[str] = Field(None, description="문서 ID")
    anchor: Dict[str, Any] = Field(
        default_factory=dict, 
        description="위치 정보: {page, paragraph, char_start, char_end}"
    )
    confidence: float = Field(1.0, description="신뢰도 (0.0 ~ 1.0)")


class ReportRequest(BaseModel):
    """
    리포트 생성 요청 데이터
    
    Example:
    ```json
    {
        "session_id": "sess_abc123",
        "qualitative_eval": {"추론_깊이": {"점수": 8, "피드백": "..."}},
        "quantitative_eval": {"어휘_다양성": {"점수": 7}},
        "integrated_eval": {"총점": 78, "등급": "B+"},
        "thought_log": [{"turn": 1, "question": "...", "answer": "..."}]
    }
    ```
    """
    session_id: Optional[str] = Field(None, description="연결할 세션 ID")
    qualitative_eval: Dict[str, Any] = Field(..., description="질적 평가 결과")
    quantitative_eval: Dict[str, Any] = Field(..., description="정량 평가 결과")
    integrated_eval: Dict[str, Any] = Field(..., description="통합 평가 결과")
    thought_log: List[Dict[str, Any]] = Field(default_factory=list, description="사고 과정 로그")


class ScoreItem(BaseModel):
    """
    점수 항목
    
    프론트엔드에서 레이더 차트/막대 그래프용
    """
    label: str = Field(..., description="항목 라벨 (영문)", example="reasoning_depth")
    score: float = Field(..., description="점수 (0-10)", example=8.5)
    label_text: str = Field(..., description="항목 라벨 (한글)", example="추론 깊이")
    reason: str = Field(..., description="평가 근거")
    citations: List[Citation] = Field(default_factory=list, description="근거 인용")


class FlowItem(BaseModel):
    """
    사고 흐름 분석 항목
    
    프론트엔드에서 단계별 시각화용
    """
    step: str = Field(..., description="단계명", example="사실 확인")
    status: str = Field(..., description="상태: perfect | good | weak")
    comment: str = Field(..., description="교사 코멘트")
    quote: Optional[str] = Field(None, description="학생 답변 인용")


class ReportResponse(BaseModel):
    """
    리포트 응답 데이터
    
    Example:
    ```json
    {
        "report_id": "rpt_abc123",
        "session_id": "sess_abc123",
        "summary": "전반적으로 우수한 분석력을 보였습니다.",
        "tags": ["심층 분석", "논리적 사고"],
        "scores": [...],
        "flow_analysis": [...],
        "prescription": "근거 제시 능력을 더 강화해보세요.",
        "created_at": "2026-02-06T12:00:00Z"
    }
    ```
    """
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
# 인메모리 저장소 (임시 - Cloud Run에서는 Firestore/Cloud SQL 권장)
# ============================================================
reports_store: Dict[str, Dict] = {}


# ============================================================
# API Endpoints
# ============================================================

@router.post(
    "/generate",
    response_model=ReportResponse,
    summary="📝 리포트 생성",
    description="""
    학습 리포트를 생성하고 저장합니다.
    
    ## 입력
    - 질적/정량/통합 평가 결과
    - 사고 과정 로그
    
    ## 출력
    - 표준화된 리포트 JSON
    - report_id로 이후 재조회 가능
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch('/reports/generate', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            session_id: 'sess_abc123',
            qualitative_eval: evaluationData.qualitative,
            quantitative_eval: evaluationData.quantitative,
            integrated_eval: evaluationData.integrated,
            thought_log: conversationLog
        })
    });
    const report = await res.json();
    
    // 리포트 페이지로 이동
    navigate(`/reports/${report.report_id}`);
    ```
    """
)
async def generate_report(
    request: ReportRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
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
        created_at = datetime.now().isoformat()
        
        # 통합 평가에서 점수/등급 추출
        total_score = request.integrated_eval.get("총점", 0)
        grade = request.integrated_eval.get("등급", "C+")
        
        # 인메모리 저장
        reports_store[report_id] = {
            "report_id": report_id,
            "session_id": request.session_id,
            "user_id": current_user.user_id,
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
        
        # DB에도 저장 (LearningReport 모델 활용)
        try:
            db_report = LearningReport(
                report_id=report_id,
                user_id=current_user.user_id,
                report_type="student",
                start_date=datetime.now(),
                end_date=datetime.now(),
                stats={
                    "total_score": total_score,
                    "grade": grade,
                    "session_id": request.session_id
                }
            )
            db.add(db_report)
            await db.commit()
        except Exception:
            pass  # DB 저장 실패해도 인메모리에는 저장됨
        
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
    description="""
    저장된 리포트를 조회합니다.
    
    ## 용도
    - 학생 기록 화면에서 과거 리포트 다시 보기
    - 교사 허브에서 학생 리포트 확인
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch(`/reports/${reportId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const report = await res.json();
    
    // 리포트 렌더링
    document.getElementById('summary').innerText = report.summary;
    renderScoreChart(report.scores);
    renderFlowAnalysis(report.flow_analysis);
    document.getElementById('prescription').innerText = report.prescription;
    ```
    """
)
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """리포트 조회"""
    
    # 인메모리에서 먼저 조회
    if report_id in reports_store:
        data = reports_store[report_id]
        return ReportResponse(
            report_id=data["report_id"],
            session_id=data.get("session_id"),
            summary=data.get("summary", ""),
            tags=data.get("tags", []),
            scores=data.get("scores", []),
            flow_analysis=data.get("flow_analysis", []),
            prescription=data.get("prescription", ""),
            total_score=data.get("total_score", 0),
            grade=data.get("grade", "C+"),
            created_at=data.get("created_at", "")
        )
    
    # DB에서 조회
    stmt = select(LearningReport).where(LearningReport.report_id == report_id)
    result = await db.execute(stmt)
    db_report = result.scalar_one_or_none()
    
    if not db_report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"리포트를 찾을 수 없습니다: {report_id}"
        )
    
    stats = db_report.stats or {}
    
    return ReportResponse(
        report_id=report_id,
        session_id=stats.get("session_id"),
        summary=f"학습 리포트 (ID: {report_id})",
        tags=[],
        scores=[],
        flow_analysis=[],
        prescription="리포트 상세 정보는 세션 기록을 확인하세요.",
        total_score=stats.get("total_score", 0),
        grade=stats.get("grade", "C+"),
        created_at=db_report.created_at.isoformat() if db_report.created_at else ""
    )


@router.get(
    "",
    summary="📚 내 리포트 목록",
    description="""
    현재 사용자의 리포트 목록을 조회합니다.
    
    ## 필터링
    - `days`: 최근 N일 이내 리포트
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch('/reports?days=30', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const { reports } = await res.json();
    
    // 리포트 카드 렌더링
    reports.forEach(rpt => {
        addReportCard(rpt.report_id, rpt.summary, rpt.grade);
    });
    ```
    """
)
async def list_reports(
    days: int = Query(30, description="최근 N일 이내"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """내 리포트 목록 조회"""
    
    # 인메모리에서 조회
    user_reports = [
        ReportListItem(
            report_id=data["report_id"],
            session_id=data.get("session_id"),
            summary=data.get("summary", "")[:50] + "...",
            total_score=data.get("total_score", 0),
            grade=data.get("grade", "C+"),
            created_at=data.get("created_at", "")
        )
        for data in reports_store.values()
        if data.get("user_id") == current_user.user_id
    ]
    
    # DB에서도 조회
    cutoff = datetime.now() - timedelta(days=days)
    stmt = select(LearningReport).where(
        LearningReport.user_id == current_user.user_id,
        LearningReport.created_at >= cutoff
    ).order_by(desc(LearningReport.created_at))
    
    result = await db.execute(stmt)
    db_reports = result.scalars().all()
    
    for db_rpt in db_reports:
        # 이미 인메모리에 있으면 스킵
        if db_rpt.report_id in reports_store:
            continue
        
        stats = db_rpt.stats or {}
        user_reports.append(ReportListItem(
            report_id=db_rpt.report_id,
            session_id=stats.get("session_id"),
            summary=f"리포트 {db_rpt.report_id}",
            total_score=stats.get("total_score", 0),
            grade=stats.get("grade", "C+"),
            created_at=db_rpt.created_at.isoformat() if db_rpt.created_at else ""
        ))
    
    return {
        "reports": user_reports,
        "total": len(user_reports)
    }
