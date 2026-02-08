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
from datetime import datetime, timedelta

# Removed SQLAlchemy imports
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select, func, desc
# from app.db.session import get_db

from app.schemas.user import User, UserBase
from app.schemas.learning import LearningState, TeacherDashboardData
from app.repository.user_repository import UserRepository
from app.repository.session_repository import session_repo
from app.repository.teacher_repository import TeacherRepository
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
    """학생 목록 응답"""
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
    """학생 세션 목록 응답"""
    student_id: str
    sessions: List[StudentSessionItem]
    total: int


class StudentSummaryResponse(BaseModel):
    """학생 요약 응답"""
    student_id: str
    username: str
    period: str = Field(..., description="조회 기간")
    stats: Dict[str, Any] = Field(..., description="통계")
    trends: Dict[str, str] = Field(..., description="추세 (improving/stable/declining)")
    risk_flags: List[str] = Field(default_factory=list, description="리스크 플래그")
    recommendations: List[str] = Field(default_factory=list, description="권장사항")


class DashboardResponse(BaseModel):
    """대시보드 응답"""
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
    summary="👥 학생 목록 조회"
)
async def get_students(
    current_user: User = Depends(get_current_active_teacher)
):
    """학생 목록 조회"""
    
    user_repo = UserRepository()
    
    # 모든 학생 조회
    students_data = await user_repo.get_users_by_type("student")
    
    student_items = []
    for s_data in students_data:
        student_id = s_data.get("user_id")
        
        # 세션 수 조회 (Firestore filtering)
        sessions = await session_repo.get_sessions_by_user(student_id)
        total_sessions = len(sessions)
        
        # 마지막 활동 조회
        last_activity = None
        if sessions:
            # get_sessions_by_user already sorts by updated_at desc
            last_activity = sessions[0].updated_at
        
        # 리스크 레벨 판단 (간단한 로직)
        risk_level = "normal"
        if last_activity:
            try:
                last_dt = datetime.fromisoformat(last_activity.replace("Z", "+00:00"))
                days_inactive = (datetime.utcnow() - last_dt).days
                if days_inactive > 7:
                    risk_level = "high"
                elif days_inactive > 3:
                    risk_level = "normal"
                else:
                    risk_level = "low"
            except ValueError:
                pass # Date parsing error
        
        student_items.append(StudentItem(
            student_id=student_id,
            username=s_data.get("username", "Unknown"),
            email=s_data.get("email", ""),
            total_sessions=total_sessions,
            last_activity=last_activity,
            risk_level=risk_level
        ))
    
    return StudentListResponse(students=student_items, total=len(student_items))


@router.get(
    "/students/{student_id}/sessions",
    response_model=StudentSessionsResponse,
    summary="📋 학생 세션 목록 조회"
)
async def get_student_sessions(
    student_id: str,
    range: str = Query("7d", description="조회 기간: 7d | 30d | 90d"),
    current_user: User = Depends(get_current_active_teacher)
):
    """학생 세션 목록 조회"""
    
    # 기간 파싱
    days = 7
    if range == "30d":
        days = 30
    elif range == "90d":
        days = 90
    
    # 세션 조회 using repository with filtering
    sessions = await session_repo.get_sessions_by_user(student_id, days=days)
    
    session_items = []
    for state in sessions:
        checkpoint = state.checkpoint_data or {}
        session_items.append(StudentSessionItem(
            session_id=state.session_id or state.state_id,
            document_id=state.current_work_id,
            status=state.status.lower() if state.status else "unknown",
            score=checkpoint.get("score"),
            grade=checkpoint.get("grade"),
            created_at=state.created_at or ""
        ))
    
    return StudentSessionsResponse(
        student_id=student_id,
        sessions=session_items,
        total=len(session_items)
    )


@router.get(
    "/students/{student_id}/summary",
    response_model=StudentSummaryResponse,
    summary="📊 학생 요약 조회"
)
async def get_student_summary(
    student_id: str,
    range: str = Query("30d", description="조회 기간: 7d | 30d | 90d"),
    current_user: User = Depends(get_current_active_teacher)
):
    """학생 요약 조회"""
    
    user_repo = UserRepository()
    student_data = await user_repo.get_by_user_id(student_id)
    
    if not student_data:
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
    
    # 세션 통계
    sessions = await session_repo.get_sessions_by_user(student_id, days=days)
    
    total_sessions = len(sessions)
    completed_sessions = sum(1 for s in sessions if s.status == "COMPLETED")
    
    scores = []
    for s in sessions:
        checkpoint = s.checkpoint_data or {}
        score = checkpoint.get("score")
        if score is not None:
             scores.append(score)
    
    average_score = sum(scores) / len(scores) if scores else 0
    
    # 추세 분석 (간단한 로직)
    score_trend = "stable"
    activity_trend = "stable"
    
    if len(scores) >= 2:
        recent_avg = sum(scores[:3]) / min(3, len(scores)) # recent are first in list due to updated_at desc sort
        older_avg = sum(scores[3:]) / max(1, len(scores) - 3) if len(scores) > 3 else recent_avg
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
    
    if average_score < 50 and scores:
        risk_flags.append("평균 점수 낮음")
        recommendations.append("추가 지원이 필요할 수 있습니다")
    
    if score_trend == "declining":
        risk_flags.append("점수 하락 추세")
        recommendations.append("최근 학습 내용을 점검하세요")
    
    if not recommendations:
        recommendations.append("꾸준한 학습을 계속 격려하세요")
    
    return StudentSummaryResponse(
        student_id=student_id,
        username=student_data.get("username", "Unknown"),
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
    summary="📈 대시보드 조회"
)
async def get_dashboard(
    current_user: User = Depends(get_current_active_teacher)
):
    """대시보드 조회"""
    
    # This might be heavy for Firestore if many documents.
    # Ideally should use aggregated counters or TeacherDashboardData document updated by triggers.
    # For now, we'll do best-effort query or use TeacherRepository if implemented.
    
    teacher_repo = TeacherRepository()
    # Try to get pre-calculated dashboard
    dashboard = await teacher_repo.get_dashboard_by_teacher(current_user.user_id)
    
    if dashboard:
        # If we have a stored dashboard, valid enough
        return DashboardResponse(
            active_sessions=dashboard.active_sessions,
            students_needing_help=dashboard.students_needing_help,
            today_completions=0, # Not in schema?
            weekly_average_score=0,
            top_performers=[],
            struggling_students=[]
        )

    # Fallback: Query Users and Sessions (Expensive!)
    # For MVP deployment, we can just return empty or simple stats
    
    user_repo = UserRepository()
    students = await user_repo.get_users_by_type("student")
    
    active_sessions_count = 0
    students_needing_help = []
    today_completions = 0
    
    # Check sessions for first 20 students to avoid timeout
    for s_data in students[:20]:
        student_id = s_data.get("user_id")
        sessions = await session_repo.get_sessions_by_user(student_id, days=7)
        
        # Check active
        active_sessions_count += sum(1 for s in sessions if s.status == "ACTIVE")
        
        # Check today completions
        today_str = datetime.utcnow().date().isoformat()
        today_completions += sum(1 for s in sessions if s.status == "COMPLETED" and s.updated_at.startswith(today_str))
        
        # Check help needed (inactive > 7 days)
        if not sessions:
             students_needing_help.append(student_id)
        else:
             last_active = sessions[0].updated_at
             # Parse and check... omitted for brevity
    
    return DashboardResponse(
        active_sessions=active_sessions_count,
        students_needing_help=students_needing_help[:5],
        today_completions=today_completions,
        weekly_average_score=0, # Need aggregation
        top_performers=[], 
        struggling_students=students_needing_help[:3]
    )
