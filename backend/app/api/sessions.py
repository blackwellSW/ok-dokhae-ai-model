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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from datetime import datetime, timedelta
import uuid

from app.db.session import get_db
from app.db.models import User, LearningState, LearningReport
from app.core.auth import get_current_user, get_current_active_student
from app.services.thought_inducer import ThoughtInducer
from app.services.integrated_evaluator import IntegratedEvaluator
from app.services.report_generator import ReportGenerator

router = APIRouter(prefix="/sessions", tags=["📚 Session Management"])


# ============================================================
# Request/Response Models
# ============================================================

class CreateSessionRequest(BaseModel):
    """
    세션 생성 요청
    
    Example:
    ```json
    {
        "document_id": "doc_abc123",
        "chunk_id": "doc_abc123_chunk_001",
        "mode": "student_led"
    }
    ```
    """
    document_id: str = Field(..., description="학습할 문서 ID")
    chunk_id: Optional[str] = Field(None, description="특정 청크부터 시작 (선택)")
    mode: str = Field("student_led", description="학습 모드: student_led(학생 주도) | ai_led(AI 주도)")


class CreateSessionResponse(BaseModel):
    """
    세션 생성 응답
    
    Example:
    ```json
    {
        "session_id": "sess_abc123",
        "status": "active",
        "first_question": "이 작품에서 주인공의 행동에 대해 어떻게 생각하시나요?",
        "message": "학습 세션이 시작되었습니다."
    }
    ```
    """
    session_id: str = Field(..., description="세션 고유 ID. 이후 모든 API 호출에 사용")
    status: str = Field(..., description="세션 상태: active | completed | paused")
    first_question: str = Field(..., description="첫 번째 사고유도 질문")
    message: str


class SessionListItem(BaseModel):
    """세션 목록 항목"""
    session_id: str = Field(..., description="세션 ID")
    document_id: Optional[str] = Field(None, description="연결된 문서 ID")
    title: str = Field(..., description="세션 제목")
    status: str = Field(..., description="상태: active | completed | paused")
    current_turn: int = Field(..., description="현재 진행 턴")
    max_turns: int = Field(..., description="최대 턴 수")
    created_at: str = Field(..., description="생성 시각")
    updated_at: str = Field(..., description="마지막 활동 시각")
    report_id: Optional[str] = Field(None, description="연결된 리포트 ID (완료 시)")


class SessionListResponse(BaseModel):
    """
    세션 목록 응답
    
    Example:
    ```json
    {
        "sessions": [
            {
                "session_id": "sess_abc123",
                "title": "춘향전 학습",
                "status": "completed",
                "current_turn": 4,
                "max_turns": 4,
                "created_at": "2026-02-06T10:00:00Z",
                "report_id": "rpt_abc123"
            }
        ],
        "total": 1
    }
    ```
    """
    sessions: List[SessionListItem]
    total: int


class MessageItem(BaseModel):
    """대화 메시지"""
    message_id: str = Field(..., description="메시지 ID")
    role: str = Field(..., description="발신자: user | assistant")
    content: str = Field(..., description="메시지 내용")
    timestamp: str = Field(..., description="전송 시각")
    metadata: Optional[Dict] = Field(None, description="추가 메타데이터 (평가 결과 등)")


class SessionMessagesResponse(BaseModel):
    """
    세션 메시지 목록 응답
    
    - 리포트에서 "대화 다시보기" 기능에 사용
    - 시간순 정렬
    
    Example:
    ```json
    {
        "session_id": "sess_abc123",
        "messages": [
            {
                "message_id": "msg_001",
                "role": "assistant",
                "content": "이 작품에서 주인공의 행동에 대해 어떻게 생각하시나요?",
                "timestamp": "2026-02-06T10:00:00Z"
            },
            {
                "message_id": "msg_002",
                "role": "user",
                "content": "주인공이 신분을 숨긴 것은...",
                "timestamp": "2026-02-06T10:01:30Z"
            }
        ],
        "total": 2
    }
    ```
    """
    session_id: str
    messages: List[MessageItem]
    total: int


class SendMessageRequest(BaseModel):
    """
    메시지 전송 요청
    
    Example:
    ```json
    {
        "content": "주인공이 신분을 숨긴 이유는 춘향의 진심을 확인하기 위해서라고 생각합니다."
    }
    ```
    """
    content: str = Field(..., description="학생의 답변 또는 질문")


class SendMessageResponse(BaseModel):
    """
    메시지 전송 응답
    
    Example:
    ```json
    {
        "message_id": "msg_003",
        "assistant_message": "좋은 분석입니다! 그렇다면 왜 '진심 확인'이 그에게 중요했을까요?",
        "message_type": "question",
        "current_turn": 2,
        "session_status": "active",
        "evaluation": null
    }
    ```
    """
    message_id: str
    assistant_message: str = Field(..., description="AI의 응답")
    message_type: str = Field(..., description="응답 유형: question | feedback | encouragement")
    current_turn: int = Field(..., description="현재 턴 (4턴 완료 시 세션 종료)")
    session_status: str = Field(..., description="세션 상태")
    evaluation: Optional[Dict] = Field(None, description="평가 결과 (마지막 턴일 경우)")


class FinalizeSessionResponse(BaseModel):
    """
    세션 종료 응답
    
    Example:
    ```json
    {
        "session_id": "sess_abc123",
        "status": "completed",
        "report_id": "rpt_abc123",
        "summary": "4턴의 대화를 성공적으로 완료했습니다.",
        "message": "세션이 종료되었습니다. 리포트를 확인하세요."
    }
    ```
    """
    session_id: str
    status: str
    report_id: Optional[str] = Field(None, description="생성된 리포트 ID")
    summary: str
    message: str


# ============================================================
# 메모리 기반 메시지 저장소 (임시 - 추후 DB 모델로 교체)
# ============================================================
# Cloud Run stateless 환경에서는 Redis나 Firestore 권장
session_messages: Dict[str, List[Dict]] = {}


# ============================================================
# API Endpoints
# ============================================================

@router.post(
    "",
    response_model=CreateSessionResponse,
    summary="🆕 새 세션 생성",
    description="""
    새 학습 세션을 생성합니다.
    
    ## 학습 모드
    - `student_led`: 학생이 질문하고 AI가 사고를 유도
    - `ai_led`: AI가 질문하고 학생이 답변
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch('/sessions', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            document_id: 'doc_abc123',
            mode: 'student_led'
        })
    });
    const { session_id, first_question } = await res.json();
    
    // 첫 질문 표시
    displayMessage('assistant', first_question);
    
    // 세션 ID 저장
    currentSessionId = session_id;
    ```
    """
)
async def create_session(
    request: CreateSessionRequest,
    current_user: User = Depends(get_current_active_student),
    db: AsyncSession = Depends(get_db)
):
    """새 학습 세션 생성"""
    
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    
    # LearningState 생성
    state = LearningState(
        state_id=session_id,
        user_id=current_user.user_id,
        current_work_id=request.document_id,
        current_chunk_id=request.chunk_id,
        session_id=session_id,
        status="ACTIVE",
        current_turn=1,
        max_turns=4,
        checkpoint_data={"mode": request.mode}
    )
    db.add(state)
    await db.commit()
    
    # 첫 번째 질문 생성
    inducer = ThoughtInducer()
    result = await inducer.generate_response(
        student_input="[세션 시작]",
        work_title=request.document_id
    )
    first_question = result.get("induction", "이 작품에서 가장 인상 깊었던 부분은 무엇인가요?")
    
    # 메시지 저장
    session_messages[session_id] = [{
        "message_id": f"msg_{uuid.uuid4().hex[:8]}",
        "role": "assistant",
        "content": first_question,
        "timestamp": datetime.now().isoformat()
    }]
    
    return CreateSessionResponse(
        session_id=session_id,
        status="active",
        first_question=first_question,
        message="학습 세션이 시작되었습니다. 4턴의 대화가 진행됩니다."
    )


@router.get(
    "",
    response_model=SessionListResponse,
    summary="📋 내 세션 목록 조회",
    description="""
    현재 사용자의 학습 세션 목록을 조회합니다.
    
    ## 필터링
    - `status`: 특정 상태만 조회 (active, completed, paused)
    - `days`: 최근 N일 이내 세션만 조회
    
    ## 사용 예시 (JavaScript)
    ```javascript
    // 최근 7일 완료된 세션만 조회
    const res = await fetch('/sessions?status=completed&days=7', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const { sessions } = await res.json();
    
    // 학생 기록 화면 렌더링
    sessions.forEach(sess => {
        addSessionCard(sess.session_id, sess.title, sess.report_id);
    });
    ```
    """
)
async def list_sessions(
    status: Optional[str] = Query(None, description="상태 필터: active | completed | paused"),
    days: int = Query(30, description="최근 N일 이내"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """내 세션 목록 조회"""
    
    # 기본 쿼리
    stmt = select(LearningState).where(
        LearningState.user_id == current_user.user_id
    )
    
    # 상태 필터
    if status:
        status_upper = status.upper()
        stmt = stmt.where(LearningState.status == status_upper)
    
    # 날짜 필터
    cutoff = datetime.now() - timedelta(days=days)
    stmt = stmt.where(LearningState.created_at >= cutoff)
    
    # 정렬
    stmt = stmt.order_by(desc(LearningState.updated_at))
    
    result = await db.execute(stmt)
    states = result.scalars().all()
    
    sessions = []
    for state in states:
        sessions.append(SessionListItem(
            session_id=state.session_id or state.state_id,
            document_id=state.current_work_id,
            title=f"{state.current_work_id or '학습'} 세션",
            status=state.status.lower() if state.status else "active",
            current_turn=state.current_turn or 1,
            max_turns=state.max_turns or 4,
            created_at=state.created_at.isoformat() if state.created_at else "",
            updated_at=state.updated_at.isoformat() if state.updated_at else "",
            report_id=state.checkpoint_data.get("report_id") if state.checkpoint_data else None
        ))
    
    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.get(
    "/{session_id}",
    summary="📄 세션 상세 조회",
    description="""
    특정 세션의 상세 정보를 조회합니다.
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch(`/sessions/${sessionId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const session = await res.json();
    
    console.log('현재 턴:', session.current_turn);
    console.log('상태:', session.status);
    ```
    """
)
async def get_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """세션 상세 조회"""
    
    stmt = select(LearningState).where(LearningState.session_id == session_id)
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()
    
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
        "created_at": state.created_at.isoformat() if state.created_at else None,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
        "last_question": state.last_question,
        "last_answer": state.last_answer
    }


@router.get(
    "/{session_id}/messages",
    response_model=SessionMessagesResponse,
    summary="💬 세션 대화 로그 조회",
    description="""
    세션의 전체 대화 기록을 조회합니다.
    
    ## 용도
    - 리포트에서 "대화 다시보기" 기능
    - 학습 과정 복기
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch(`/sessions/${sessionId}/messages`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const { messages } = await res.json();
    
    // 대화 UI 렌더링
    messages.forEach(msg => {
        displayMessage(msg.role, msg.content, msg.timestamp);
    });
    ```
    """
)
async def get_session_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """세션 대화 로그 조회"""
    
    # 세션 존재 확인
    stmt = select(LearningState).where(LearningState.session_id == session_id)
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()
    
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"세션을 찾을 수 없습니다: {session_id}"
        )
    
    # 메모리에서 메시지 조회
    messages = session_messages.get(session_id, [])
    
    return SessionMessagesResponse(
        session_id=session_id,
        messages=[
            MessageItem(
                message_id=msg["message_id"],
                role=msg["role"],
                content=msg["content"],
                timestamp=msg["timestamp"],
                metadata=msg.get("metadata")
            )
            for msg in messages
        ],
        total=len(messages)
    )


@router.post(
    "/{session_id}/messages",
    response_model=SendMessageResponse,
    summary="✉️ 메시지 전송",
    description="""
    세션에 메시지를 전송하고 AI 응답을 받습니다.
    
    ## 작동 방식
    1. 학생 메시지 저장
    2. AI 사고유도 응답 생성
    3. 턴 카운트 증가
    4. 4턴 완료 시 자동 종료 + 평가
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch(`/sessions/${sessionId}/messages`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            content: '주인공이 신분을 숨긴 이유는...'
        })
    });
    const data = await res.json();
    
    // AI 응답 표시
    displayMessage('assistant', data.assistant_message);
    
    // 세션 종료 확인
    if (data.session_status === 'completed') {
        showReportButton(data.evaluation.report_id);
    }
    ```
    """
)
async def send_message(
    session_id: str,
    request: SendMessageRequest,
    current_user: User = Depends(get_current_active_student),
    db: AsyncSession = Depends(get_db)
):
    """메시지 전송 및 AI 응답"""
    
    # 세션 조회
    stmt = select(LearningState).where(LearningState.session_id == session_id)
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()
    
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
    
    # 사용자 메시지 저장
    user_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    if session_id not in session_messages:
        session_messages[session_id] = []
    
    session_messages[session_id].append({
        "message_id": user_msg_id,
        "role": "user",
        "content": request.content,
        "timestamp": datetime.now().isoformat()
    })
    
    # 턴 증가
    state.current_turn = (state.current_turn or 1) + 1
    state.last_answer = request.content
    
    evaluation = None
    session_status = "active"
    
    # 4턴 완료 시 평가 및 종료
    if state.current_turn > state.max_turns:
        state.status = "COMPLETED"
        session_status = "completed"
        
        # 통합 평가
        evaluator = IntegratedEvaluator()
        eval_result = await evaluator.evaluate_comprehensive(request.content)
        
        # 리포트 생성
        report_id = f"rpt_{uuid.uuid4().hex[:12]}"
        state.checkpoint_data = state.checkpoint_data or {}
        state.checkpoint_data["report_id"] = report_id
        
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
        state.last_question = assistant_message
    
    # AI 메시지 저장
    assistant_msg_id = f"msg_{uuid.uuid4().hex[:8]}"
    session_messages[session_id].append({
        "message_id": assistant_msg_id,
        "role": "assistant",
        "content": assistant_message,
        "timestamp": datetime.now().isoformat(),
        "metadata": evaluation
    })
    
    await db.commit()
    
    return SendMessageResponse(
        message_id=assistant_msg_id,
        assistant_message=assistant_message,
        message_type=message_type,
        current_turn=state.current_turn,
        session_status=session_status,
        evaluation=evaluation
    )


@router.post(
    "/{session_id}/finalize",
    response_model=FinalizeSessionResponse,
    summary="🏁 세션 수동 종료",
    description="""
    학습 세션을 수동으로 종료하고 리포트를 생성합니다.
    
    ## 언제 사용하나요?
    - 4턴 완료 전 조기 종료할 때
    - 세션을 강제로 종료할 때
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch(`/sessions/${sessionId}/finalize`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const { report_id } = await res.json();
    
    // 리포트 페이지로 이동
    window.location.href = `/reports/${report_id}`;
    ```
    """
)
async def finalize_session(
    session_id: str,
    current_user: User = Depends(get_current_active_student),
    db: AsyncSession = Depends(get_db)
):
    """세션 수동 종료"""
    
    stmt = select(LearningState).where(LearningState.session_id == session_id)
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()
    
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
    
    # 세션 종료
    state.status = "COMPLETED"
    
    # 리포트 생성
    report_id = f"rpt_{uuid.uuid4().hex[:12]}"
    state.checkpoint_data = state.checkpoint_data or {}
    state.checkpoint_data["report_id"] = report_id
    
    await db.commit()
    
    return FinalizeSessionResponse(
        session_id=session_id,
        status="completed",
        report_id=report_id,
        summary=f"{state.current_turn}턴의 대화를 완료했습니다.",
        message="세션이 종료되었습니다. 리포트를 확인하세요."
    )


@router.get(
    "/{session_id}/report",
    summary="📊 세션 리포트 조회",
    description="""
    세션에 연결된 리포트 정보를 조회합니다.
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch(`/sessions/${sessionId}/report`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const { report_id } = await res.json();
    
    // 리포트 상세 조회
    const reportRes = await fetch(`/reports/${report_id}`);
    const report = await reportRes.json();
    ```
    """
)
async def get_session_report(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """세션 리포트 조회"""
    
    stmt = select(LearningState).where(LearningState.session_id == session_id)
    result = await db.execute(stmt)
    state = result.scalar_one_or_none()
    
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
