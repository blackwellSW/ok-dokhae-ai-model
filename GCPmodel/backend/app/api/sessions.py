"""
세션(학습 대화) 관리 API
역할: 학습 세션 생성/조회/메시지 로그 관리

📋 프론트엔드 개발자를 위한 사용 가이드
==========================================

1. 세션 생성: POST /sessions
   - document_id와 함께 세션 시작
   - session_id 받음

2. 내 세션 목록: GET /sessions
   - 학생 기록 화면/교사용 허브에서 사용

3. 세션 상세: GET /sessions/{session_id}
   - 세션 메타데이터 조회

4. 대화 로그: GET /sessions/{session_id}/messages
   - 리포트에서 "대화 다시보기"

5. 메시지 전송: POST /sessions/{session_id}/messages
   - 기존 /chat/send의 세션 기반 버전

6. 세션 종료: POST /sessions/{session_id}/finalize
   - 세션 종료 + 리포트 생성
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import uuid

# Removed SQLAlchemy imports
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select, desc
# from app.db.session import get_db

from app.schemas.user import User
from app.schemas.learning import LearningState
from app.repository.session_repository import session_repo
from app.core.auth import get_current_user, get_current_active_student
from app.services.thought_inducer import ThoughtInducer
from app.services.integrated_evaluator import IntegratedEvaluator
from app.services.report_generator import ReportGenerator
from app.services.gemini_evaluator import GeminiEvaluator
from app.repository.report_repository import report_repo
from app.services.firestore_session import (
    init_session_messages,
    append_user_message,
    append_assistant_message,
    get_messages
)

router = APIRouter(prefix="/sessions", tags=["📚 Session Management"])


# ============================================================
# Request/Response Models
# ============================================================

class CreateSessionRequest(BaseModel):
    """세션 생성 요청"""
    document_id: str = Field(..., description="학습할 문서 ID")
    chunk_id: Optional[str] = Field(None, description="특정 청크부터 시작 (선택)")
    mode: str = Field("student_led", description="학습 모드: student_led(학생 주도) | ai_led(AI 주도)")


class CreateSessionResponse(BaseModel):
    """세션 생성 응답"""
    session_id: str = Field(..., description="세션 고유 ID")
    status: str = Field(..., description="세션 상태")
    first_question: str = Field(..., description="첫 번째 사고유도 질문")
    message: str


class SessionListItem(BaseModel):
    """세션 목록 항목"""
    session_id: str = Field(..., description="세션 ID")
    document_id: Optional[str] = Field(None, description="연결된 문서 ID")
    title: str = Field(..., description="세션 제목")
    status: str = Field(..., description="상태")
    current_turn: int = Field(..., description="현재 진행 턴")
    max_turns: int = Field(..., description="최대 턴 수")
    created_at: str = Field(..., description="생성 시각")
    updated_at: str = Field(..., description="마지막 활동 시각")
    report_id: Optional[str] = Field(None, description="연결된 리포트 ID")


class SessionListResponse(BaseModel):
    """세션 목록 응답"""
    sessions: List[SessionListItem]
    total: int


class MessageItem(BaseModel):
    """대화 메시지"""
    message_id: str
    role: str
    content: str
    timestamp: str
    metadata: Optional[Dict] = None


class SessionMessagesResponse(BaseModel):
    """세션 메시지 목록 응답"""
    session_id: str
    messages: List[MessageItem]
    total: int


class SendMessageRequest(BaseModel):
    """메시지 전송 요청"""
    content: str = Field(..., description="학생의 답변 또는 질문")


class SendMessageResponse(BaseModel):
    """메시지 전송 응답"""
    message_id: str
    assistant_message: str
    message_type: str
    current_turn: int
    session_status: str
    evaluation: Optional[Dict] = None


class FinalizeSessionResponse(BaseModel):
    """세션 종료 응답"""
    session_id: str
    status: str
    report_id: Optional[str] = None
    summary: str
    message: str


# ============================================================
# API Endpoints
# ============================================================

@router.post(
    "",
    response_model=CreateSessionResponse,
    summary="🆕 새 세션 생성"
)
async def create_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_active_student)
):
    """새 학습 세션 생성"""
    
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    
    # Create LearningState data
    state_data = {
        "state_id": session_id,
        "user_id": current_user.user_id,
        "current_work_id": request.document_id,
        "current_chunk_id": request.chunk_id,
        "session_id": session_id,
        "status": "ACTIVE",
        "current_turn": 1,
        "max_turns": 4,
        "checkpoint_data": {"mode": request.mode}
    }
    
    # Save to Firestore via Repository
    await session_repo.create_session(state_data)
    
    # 첫 번째 질문 생성
    inducer = ThoughtInducer()
    result = await inducer.generate_response(
        student_input="[세션 시작]",
        work_title=request.document_id
    )
    first_question = result.get("induction", "이 작품에서 가장 인상 깊었던 부분은 무엇인가요?")

    # 메시지 저장 (Firestore Messages Subcollection)
    first_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    await init_session_messages(session_id, {
        "message_id": first_msg_id,
        "role": "assistant",
        "content": first_question
    })

    return CreateSessionResponse(
        session_id=session_id,
        status="active",
        first_question=first_question,
        message="학습 세션이 시작되었습니다. 4턴의 대화가 진행됩니다."
    )


@router.get(
    "",
    response_model=SessionListResponse,
    summary="📋 내 세션 목록 조회"
)
async def list_sessions(
    status: Optional[str] = Query(None, description="상태 필터: active | completed | paused"),
    days: int = Query(30, description="최근 N일 이내"),
    current_user: User = Depends(get_current_user)
):
    """내 세션 목록 조회"""
    
    # Use Repository with filtering
    states = await session_repo.get_sessions_by_user(
        user_id=current_user.user_id,
        status=status.upper() if status else None,
        days=days
    )
    
    sessions = []
    for state in states:
        sessions.append(SessionListItem(
            session_id=state.session_id or state.state_id,
            document_id=state.current_work_id,
            title=f"{state.current_work_id or '학습'} 세션",
            status=state.status.lower() if state.status else "active",
            current_turn=state.current_turn,
            max_turns=state.max_turns,
            created_at=state.created_at or "",
            updated_at=state.updated_at or "",
            report_id=state.checkpoint_data.get("report_id") if state.checkpoint_data else None
        ))
    
    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.get(
    "/{session_id}",
    summary="📄 세션 상세 조회"
)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """세션 상세 조회"""
    
    state = await session_repo.get_session(session_id)
    
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"세션을 찾을 수 없습니다: {session_id}"
        )
    
    return {
        "session_id": session_id,
        "document_id": state.current_work_id,
        "chunk_id": state.current_chunk_id,
        "status": state.status.lower() if state.status else "active",
        "current_turn": state.current_turn,
        "max_turns": state.max_turns,
        "mode": state.checkpoint_data.get("mode", "student_led") if state.checkpoint_data else "student_led",
        "created_at": state.created_at,
        "updated_at": state.updated_at,
        "last_question": state.last_question,
        "last_answer": state.last_answer
    }


@router.get(
    "/{session_id}/messages",
    response_model=SessionMessagesResponse,
    summary="💬 세션 대화 로그 조회"
)
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """세션 대화 로그 조회"""
    
    # Check session existence
    state = await session_repo.get_session(session_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"세션을 찾을 수 없습니다: {session_id}"
        )

    # Firestore에서 메시지 조회
    messages = await get_messages(session_id)

    return SessionMessagesResponse(
        session_id=session_id,
        messages=[
            MessageItem(
                message_id=msg.get("message_id", ""),
                role=msg.get("role", ""),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp", ""),
                metadata=msg.get("metadata")
            )
            for msg in messages
        ],
        total=len(messages)
    )


@router.post(
    "/{session_id}/messages",
    response_model=SendMessageResponse,
    summary="✉️ 메시지 전송"
)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_active_student)
):
    """메시지 전송 및 AI 응답"""
    
    # 세션 조회
    state = await session_repo.get_session(session_id)
    
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"세션을 찾을 수 없습니다: {session_id}"
        )
    
    if state.status == "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 종료된 세션입니다"
        )

    # 사용자 메시지 저장 (Firestore)
    user_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    await append_user_message(session_id, user_msg_id, request.content)
    
    # 턴 증가 및 상태 업데이트 준비
    new_turn = state.current_turn + 1
    update_data = {
        "current_turn": new_turn,
        "last_answer": request.content
    }
    
    evaluation = None
    session_status = "active"
    assistant_message = ""
    message_type = ""
    
    # 4턴 완료 시 평가 및 종료
    if new_turn > state.max_turns:
        update_data["status"] = "COMPLETED"
        session_status = "completed"

        # 통합 평가
        evaluator = IntegratedEvaluator()
        eval_result = await evaluator.evaluate_comprehensive(request.content)

        # 리포트 생성
        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        checkpoint_data = state.checkpoint_data or {}
        checkpoint_data["report_id"] = report_id
        update_data["checkpoint_data"] = checkpoint_data

        # 리포트 데이터 생성 및 저장
        generator = ReportGenerator()
        report_data = generator.generate(
            qualitative_eval=eval_result.get("질적_평가", {}),
            quantitative_eval=eval_result.get("정량_분석", {}),
            integrated_eval=eval_result.get("통합_평가", {}),
            thought_log=[]
        )

        # Firestore에 리포트 저장
        report_dict = {
            "report_id": report_id,
            "session_id": session_id,
            "user_id": current_user.user_id,
            "report_type": "student",
            "summary": report_data.get("summary", ""),
            "tags": report_data.get("tags", []),
            "scores": report_data.get("scores", []),
            "flow_analysis": report_data.get("flow_analysis", []),
            "prescription": report_data.get("prescription", ""),
            "total_score": eval_result.get("통합_평가", {}).get("총점", 0),
            "grade": eval_result.get("통합_평가", {}).get("등급", "C+"),
            "created_at": datetime.utcnow().isoformat(),
            "raw_data": {
                "qualitative": eval_result.get("질적_평가", {}),
                "quantitative": eval_result.get("정량_분석", {}),
                "integrated": eval_result.get("통합_평가", {})
            }
        }
        await report_repo.create_report(report_dict)

        evaluation = {
            "report_id": report_id,
            "score": eval_result.get("통합_평가", {}).get("총점", 0),
            "grade": eval_result.get("통합_평가", {}).get("등급", "C+"),
            "feedback": eval_result.get("개인_피드백", [])
        }

        assistant_message = f"수고하셨습니다! 📊 총점: {evaluation['score']}점 (등급: {evaluation['grade']})"
        message_type = "feedback"
    else:
        # AI 사고유도 응답 생성
        inducer = ThoughtInducer()
        result = await inducer.generate_response(
            student_input=request.content,
            work_title=state.current_work_id
        )
        assistant_message = result.get("induction", "좋은 생각이에요! 좀 더 구체적으로 설명해볼까요?")
        message_type = "question"
        update_data["last_question"] = assistant_message
    
    # AI 메시지 저장 (Firestore)
    assistant_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    await append_assistant_message(session_id, assistant_msg_id, assistant_message, evaluation)

    # DB 업데이트
    await session_repo.update_session(session_id, update_data)
    
    return SendMessageResponse(
        message_id=assistant_msg_id,
        assistant_message=assistant_message,
        message_type=message_type,
        current_turn=new_turn,
        session_status=session_status,
        evaluation=evaluation
    )


@router.post(
    "/{session_id}/finalize",
    response_model=FinalizeSessionResponse,
    summary="🏁 세션 수동 종료"
)
async def finalize_session(
    session_id: str,
    current_user: User = Depends(get_current_active_student)
):
    """세션 수동 종료"""
    
    state = await session_repo.get_session(session_id)
    
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"세션을 찾을 수 없습니다: {session_id}"
        )
    
    # 이미 완료된 경우
    if state.status == "COMPLETED":
        report_id = state.checkpoint_data.get("report_id") if state.checkpoint_data else None
        return FinalizeSessionResponse(
            session_id=session_id,
            status="completed",
            report_id=report_id,
            summary=f"이미 완료된 세션입니다. (총 {state.current_turn}턴)",
            message="이미 종료된 세션입니다."
        )
    
    # Gemini 기반 종합 리포트 생성
    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    created_at = datetime.utcnow().isoformat()

    try:
        # 1. 대화 로그 조회
        messages = await get_messages(session_id)
        logs_text = "\n".join([
            f"[{m.get('role', 'unknown')}] {m.get('content', '')}"
            for m in messages
        ])

        # 2. Gemini로 종합 리포트 생성
        gemini_eval = GeminiEvaluator()
        gemini_summary = await gemini_eval.generate_session_summary(logs_text)

        # 3. 리포트 데이터 구성
        report_dict = {
            "report_id": report_id,
            "session_id": session_id,
            "user_id": current_user.user_id,
            "report_type": "session_final",
            "summary": gemini_summary.get("종합_피드백", f"{state.current_turn}턴의 대화를 완료했습니다."),
            "tags": [f"#{s}" for s in gemini_summary.get("주요_강점", [])[:3]],
            "scores": [],
            "flow_analysis": [],
            "prescription": gemini_summary.get("향후_학습_가이드", "다음 학습을 진행해보세요."),
            "total_score": 0,
            "grade": gemini_summary.get("성취도_등급", "B"),
            "created_at": created_at,
            "raw_data": {
                "gemini_summary": gemini_summary,
                "total_turns": state.current_turn,
                "strengths": gemini_summary.get("주요_강점", []),
                "improvements": gemini_summary.get("보완_필요점", [])
            }
        }

        # 4. Firestore에 리포트 저장
        await report_repo.create_report(report_dict)

        summary_text = gemini_summary.get("종합_피드백", f"{state.current_turn}턴의 대화를 완료했습니다.")

    except Exception as e:
        # Gemini 실패 시 기본 리포트
        summary_text = f"{state.current_turn}턴의 대화를 완료했습니다."

    # 세션 상태 업데이트
    checkpoint_data = state.checkpoint_data or {}
    checkpoint_data["report_id"] = report_id

    update_data = {
        "status": "COMPLETED",
        "checkpoint_data": checkpoint_data
    }

    await session_repo.update_session(session_id, update_data)

    return FinalizeSessionResponse(
        session_id=session_id,
        status="completed",
        report_id=report_id,
        summary=summary_text,
        message="세션이 종료되었습니다. Gemini 기반 리포트가 생성되었습니다."
    )


@router.get(
    "/{session_id}/report",
    summary="📊 세션 리포트 조회"
)
async def get_session_report(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    """세션 리포트 조회"""
    
    state = await session_repo.get_session(session_id)
    
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"세션을 찾을 수 없습니다: {session_id}"
        )
    
    report_id = state.checkpoint_data.get("report_id") if state.checkpoint_data else None
    
    if not report_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="이 세션에는 아직 리포트가 없습니다. 세션을 먼저 종료하세요."
        )
    
    return {
        "session_id": session_id,
        "report_id": report_id,
        "status": state.status.lower() if state.status else "unknown"
    }
