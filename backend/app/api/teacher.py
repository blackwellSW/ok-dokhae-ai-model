"""
교사용(Teacher Hub) API
역할: 학생 관리, 세션 모니터링, 통계 조회

📋 프론트엔드 개발자를 위한 사용 가이드
==========================================

1. 학생 목록: GET /teacher/students
   - 내 반/그룹의 학생 목록

2. 학생별 세션: GET /teacher/students/{student_id}/sessions
   - 특정 학생의 최근 학습 세션

3. 학생 요약: GET /teacher/students/{student_id}/summary
   - 학생 학습 상태 요약 (리스크 플래그 포함)

4. 대시보드: GET /teacher/dashboard
   - 전체 현황 (실시간 세션, 도움 필요 학생 등)

⚠️ 권한: teacher 역할만 접근 가능
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from datetime import datetime, timedelta

from app.db.session import get_db
from app.db.models import User, LearningState, LearningReport
from app.core.auth import get_current_user

router = APIRouter(prefix="/teacher", tags=["👩‍🏫 Teacher Hub"])


# ============================================================
# 권한 체크
# ============================================================

async def get_current_active_teacher(
    current_user: User = Depends(get_current_user)
) -> User:
    """교사 권한 확인"""
    if current_user.user_type not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교사 권한이 필요합니다"
        )
    return current_user


# ============================================================
# Request/Response Models
# ============================================================

class StudentItem(BaseModel):
    """학생 정보"""
    student_id: str = Field(..., description="학생 ID")
    username: str = Field(..., description="학생 이름")
    email: str = Field(..., description="이메일")
    total_sessions: int = Field(0, description="총 세션 수")
    last_activity: Optional[str] = Field(None, description="마지막 활동 시각")
    risk_level: str = Field("normal", description="리스크 레벨: low | normal | high")


class StudentListResponse(BaseModel):
    """
    학생 목록 응답
    
    Example:
    ```json
    {
        "students": [
            {
                "student_id": "user_abc123",
                "username": "김학생",
                "email": "student@school.com",
                "total_sessions": 15,
                "last_activity": "2026-02-06T10:00:00Z",
                "risk_level": "normal"
            }
        ],
        "total": 1
    }
    ```
    """
    students: List[StudentItem]
    total: int


class StudentSessionItem(BaseModel):
    """학생 세션 요약"""
    session_id: str
    document_id: Optional[str]
    status: str
    score: Optional[float]
    grade: Optional[str]
    created_at: str


class StudentSessionsResponse(BaseModel):
    """
    학생 세션 목록 응답
    
    Example:
    ```json
    {
        "student_id": "user_abc123",
        "sessions": [
            {
                "session_id": "sess_abc123",
                "document_id": "doc_abc123",
                "status": "completed",
                "score": 85,
                "grade": "B+",
                "created_at": "2026-02-06T10:00:00Z"
            }
        ],
        "total": 1
    }
    ```
    """
    student_id: str
    sessions: List[StudentSessionItem]
    total: int


class StudentSummaryResponse(BaseModel):
    """
    학생 요약 응답
    
    - 교사 허브에서 개별 학생 카드에 표시
    - 리스크 플래그 포함
    
    Example:
    ```json
    {
        "student_id": "user_abc123",
        "username": "김학생",
        "period": "last_30_days",
        "stats": {
            "total_sessions": 15,
            "completed_sessions": 12,
            "average_score": 78.5,
            "average_grade": "B"
        },
        "trends": {
            "score_trend": "improving",
            "activity_trend": "stable"
        },
        "risk_flags": [],
        "recommendations": ["꾸준한 학습을 계속하세요"]
    }
    ```
    """
    student_id: str
    username: str
    period: str = Field(..., description="조회 기간")
    stats: Dict[str, Any] = Field(..., description="통계")
    trends: Dict[str, str] = Field(..., description="추세 (improving/stable/declining)")
    risk_flags: List[str] = Field(default_factory=list, description="리스크 플래그")
    recommendations: List[str] = Field(default_factory=list, description="권장사항")


class DashboardResponse(BaseModel):
    """
    대시보드 응답
    
    Example:
    ```json
    {
        "active_sessions": 3,
        "students_needing_help": ["user_abc123"],
        "today_completions": 5,
        "weekly_average_score": 75.2,
        "top_performers": ["user_xyz"],
        "struggling_students": ["user_abc123"]
    }
    ```
    """
    active_sessions: int = Field(0, description="현재 활성 세션 수")
    students_needing_help: List[str] = Field(default_factory=list, description="도움 필요 학생 ID")
    today_completions: int = Field(0, description="오늘 완료된 세션 수")
    weekly_average_score: float = Field(0, description="주간 평균 점수")
    top_performers: List[str] = Field(default_factory=list, description="우수 학생 ID")
    struggling_students: List[str] = Field(default_factory=list, description="어려움 겪는 학생 ID")


# ============================================================
# API Endpoints
# ============================================================

@router.get(
    "/students",
    response_model=StudentListResponse,
    summary="👥 학생 목록 조회",
    description="""
    교사의 학생 목록을 조회합니다.
    
    ## 권한
    - teacher 또는 admin 역할 필요
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch('/teacher/students', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const { students } = await res.json();
    
    // 학생 카드 렌더링
    students.forEach(student => {
        addStudentCard(student.student_id, student.username, student.risk_level);
    });
    ```
    """
)
async def get_students(
    current_user: User = Depends(get_current_active_teacher),
    db: AsyncSession = Depends(get_db)
):
    """학생 목록 조회"""
    
    # 모든 학생 조회
    stmt = select(User).where(User.user_type == "student")
    result = await db.execute(stmt)
    students = result.scalars().all()
    
    student_items = []
    for student in students:
        # 세션 수 조회
        session_stmt = select(func.count(LearningState.id)).where(
            LearningState.user_id == student.user_id
        )
        session_result = await db.execute(session_stmt)
        total_sessions = session_result.scalar() or 0
        
        # 마지막 활동 조회
        last_stmt = select(LearningState.updated_at).where(
            LearningState.user_id == student.user_id
        ).order_by(desc(LearningState.updated_at)).limit(1)
        last_result = await db.execute(last_stmt)
        last_activity = last_result.scalar()
        
        # 리스크 레벨 판단 (간단한 로직)
        risk_level = "normal"
        if last_activity:
            days_inactive = (datetime.now() - last_activity).days
            if days_inactive > 7:
                risk_level = "high"
            elif days_inactive > 3:
                risk_level = "normal"
            else:
                risk_level = "low"
        
        student_items.append(StudentItem(
            student_id=student.user_id,
            username=student.username,
            email=student.email,
            total_sessions=total_sessions,
            last_activity=last_activity.isoformat() if last_activity else None,
            risk_level=risk_level
        ))
    
    return StudentListResponse(students=student_items, total=len(student_items))


@router.get(
    "/students/{student_id}/sessions",
    response_model=StudentSessionsResponse,
    summary="📋 학생 세션 목록 조회",
    description="""
    특정 학생의 최근 학습 세션을 조회합니다.
    
    ## 파라미터
    - `range`: 조회 기간 (7d, 30d, 90d)
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch(`/teacher/students/${studentId}/sessions?range=7d`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const { sessions } = await res.json();
    
    // 세션 테이블 렌더링
    sessions.forEach(sess => {
        addSessionRow(sess.session_id, sess.score, sess.grade);
    });
    ```
    """
)
async def get_student_sessions(
    student_id: str,
    range: str = Query("7d", description="조회 기간: 7d | 30d | 90d"),
    current_user: User = Depends(get_current_active_teacher),
    db: AsyncSession = Depends(get_db)
):
    """학생 세션 목록 조회"""
    
    # 기간 파싱
    days = 7
    if range == "30d":
        days = 30
    elif range == "90d":
        days = 90
    
    cutoff = datetime.now() - timedelta(days=days)
    
    # 세션 조회
    stmt = select(LearningState).where(
        LearningState.user_id == student_id,
        LearningState.created_at >= cutoff
    ).order_by(desc(LearningState.created_at))
    
    result = await db.execute(stmt)
    states = result.scalars().all()
    
    sessions = []
    for state in states:
        checkpoint = state.checkpoint_data or {}
        sessions.append(StudentSessionItem(
            session_id=state.session_id or state.state_id,
            document_id=state.current_work_id,
            status=state.status.lower() if state.status else "unknown",
            score=checkpoint.get("score"),
            grade=checkpoint.get("grade"),
            created_at=state.created_at.isoformat() if state.created_at else ""
        ))
    
    return StudentSessionsResponse(
        student_id=student_id,
        sessions=sessions,
        total=len(sessions)
    )


@router.get(
    "/students/{student_id}/summary",
    response_model=StudentSummaryResponse,
    summary="📊 학생 요약 조회",
    description="""
    특정 학생의 학습 상태 요약을 조회합니다.
    
    ## 포함 정보
    - 통계 (세션 수, 평균 점수 등)
    - 추세 (향상/유지/하락)
    - 리스크 플래그
    - 추천사항
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch(`/teacher/students/${studentId}/summary?range=30d`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const summary = await res.json();
    
    // 학생 상세 카드 렌더링
    renderStudentSummary(summary);
    
    // 리스크 플래그 표시
    if (summary.risk_flags.length > 0) {
        showAlerts(summary.risk_flags);
    }
    ```
    """
)
async def get_student_summary(
    student_id: str,
    range: str = Query("30d", description="조회 기간: 7d | 30d | 90d"),
    current_user: User = Depends(get_current_active_teacher),
    db: AsyncSession = Depends(get_db)
):
    """학생 요약 조회"""
    
    # 학생 정보 조회
    user_stmt = select(User).where(User.user_id == student_id)
    user_result = await db.execute(user_stmt)
    student = user_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"학생을 찾을 수 없습니다: {student_id}"
        )
    
    # 기간 파싱
    days = 30
    if range == "7d":
        days = 7
    elif range == "90d":
        days = 90
    
    cutoff = datetime.now() - timedelta(days=days)
    
    # 세션 통계
    session_stmt = select(LearningState).where(
        LearningState.user_id == student_id,
        LearningState.created_at >= cutoff
    )
    session_result = await db.execute(session_stmt)
    sessions = session_result.scalars().all()
    
    total_sessions = len(sessions)
    completed_sessions = sum(1 for s in sessions if s.status == "COMPLETED")
    
    # 리포트 통계
    report_stmt = select(LearningReport).where(
        LearningReport.user_id == student_id,
        LearningReport.created_at >= cutoff
    )
    report_result = await db.execute(report_stmt)
    reports = report_result.scalars().all()
    
    scores = []
    for report in reports:
        if report.stats and "total_score" in report.stats:
            scores.append(report.stats["total_score"])
    
    average_score = sum(scores) / len(scores) if scores else 0
    
    # 추세 분석 (간단한 로직)
    score_trend = "stable"
    activity_trend = "stable"
    
    if len(scores) >= 2:
        recent_avg = sum(scores[-3:]) / min(3, len(scores))
        older_avg = sum(scores[:-3]) / max(1, len(scores) - 3) if len(scores) > 3 else recent_avg
        if recent_avg > older_avg + 5:
            score_trend = "improving"
        elif recent_avg < older_avg - 5:
            score_trend = "declining"
    
    # 리스크 플래그
    risk_flags = []
    recommendations = []
    
    if total_sessions == 0:
        risk_flags.append("최근 학습 활동 없음")
        recommendations.append("학생에게 학습 참여를 독려하세요")
    elif completed_sessions / total_sessions < 0.5:
        risk_flags.append("세션 완료율 낮음")
        recommendations.append("학생이 어려움을 겪고 있는지 확인하세요")
    
    if average_score < 50:
        risk_flags.append("평균 점수 낮음")
        recommendations.append("추가 지원이 필요할 수 있습니다")
    
    if score_trend == "declining":
        risk_flags.append("점수 하락 추세")
        recommendations.append("최근 학습 내용을 점검하세요")
    
    if not recommendations:
        recommendations.append("꾸준한 학습을 계속 격려하세요")
    
    return StudentSummaryResponse(
        student_id=student_id,
        username=student.username,
        period=f"last_{days}_days",
        stats={
            "total_sessions": total_sessions,
            "completed_sessions": completed_sessions,
            "completion_rate": completed_sessions / total_sessions if total_sessions > 0 else 0,
            "average_score": round(average_score, 1),
            "average_grade": "A" if average_score >= 90 else "B" if average_score >= 80 else "C" if average_score >= 70 else "D" if average_score >= 60 else "F"
        },
        trends={
            "score_trend": score_trend,
            "activity_trend": activity_trend
        },
        risk_flags=risk_flags,
        recommendations=recommendations
    )


@router.get(
    "/dashboard",
    response_model=DashboardResponse,
    summary="📈 대시보드 조회",
    description="""
    교사용 대시보드 데이터를 조회합니다.
    
    ## 포함 정보
    - 현재 활성 세션 수
    - 도움 필요 학생 목록
    - 오늘 완료된 세션 수
    - 주간 평균 점수
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch('/teacher/dashboard', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const dashboard = await res.json();
    
    // 대시보드 렌더링
    document.getElementById('activeSessions').innerText = dashboard.active_sessions;
    document.getElementById('todayCompletions').innerText = dashboard.today_completions;
    
    // 알람 표시
    if (dashboard.students_needing_help.length > 0) {
        showHelpNeededAlert(dashboard.students_needing_help);
    }
    ```
    """
)
async def get_dashboard(
    current_user: User = Depends(get_current_active_teacher),
    db: AsyncSession = Depends(get_db)
):
    """대시보드 조회"""
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = datetime.now() - timedelta(days=7)
    
    # 활성 세션 수
    active_stmt = select(func.count(LearningState.id)).where(
        LearningState.status == "ACTIVE"
    )
    active_result = await db.execute(active_stmt)
    active_sessions = active_result.scalar() or 0
    
    # 오늘 완료된 세션
    today_stmt = select(func.count(LearningState.id)).where(
        LearningState.status == "COMPLETED",
        LearningState.updated_at >= today
    )
    today_result = await db.execute(today_stmt)
    today_completions = today_result.scalar() or 0
    
    # 주간 평균 점수
    weekly_stmt = select(LearningReport.stats).where(
        LearningReport.created_at >= week_ago
    )
    weekly_result = await db.execute(weekly_stmt)
    weekly_stats = weekly_result.scalars().all()
    
    weekly_scores = []
    for stats in weekly_stats:
        if stats and "total_score" in stats:
            weekly_scores.append(stats["total_score"])
    
    weekly_average_score = sum(weekly_scores) / len(weekly_scores) if weekly_scores else 0
    
    # 도움 필요 학생 (7일 이상 비활성)
    inactive_cutoff = datetime.now() - timedelta(days=7)
    students_stmt = select(User.user_id).where(User.user_type == "student")
    students_result = await db.execute(students_stmt)
    all_students = [s for s in students_result.scalars().all()]
    
    students_needing_help = []
    for student_id in all_students[:10]:  # 성능을 위해 10명만 체크
        last_stmt = select(LearningState.updated_at).where(
            LearningState.user_id == student_id
        ).order_by(desc(LearningState.updated_at)).limit(1)
        last_result = await db.execute(last_stmt)
        last_activity = last_result.scalar()
        
        if not last_activity or last_activity < inactive_cutoff:
            students_needing_help.append(student_id)
    
    return DashboardResponse(
        active_sessions=active_sessions,
        students_needing_help=students_needing_help[:5],
        today_completions=today_completions,
        weekly_average_score=round(weekly_average_score, 1),
        top_performers=[],  # TODO: 구현
        struggling_students=students_needing_help[:3]
    )
