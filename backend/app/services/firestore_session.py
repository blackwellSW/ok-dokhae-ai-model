"""
Firestore 세션 메시지 관리
역할: 학습 세션의 대화 메시지를 Firestore에 저장/조회

Firestore 구조:
- sessions/{session_id}/messages/{message_id}
  - role: "user" | "assistant"
  - content: 메시지 내용
  - timestamp: 생성 시각
  - metadata: 추가 데이터 (평가 결과 등)
"""

from typing import List, Dict, Optional
from datetime import datetime
from app.core.firebase import get_firestore_client

# Firestore 사용 불가 시 메모리 fallback
_memory_fallback: Dict[str, List[Dict]] = {}


def _get_messages_collection(session_id: str):
    """세션의 메시지 컬렉션 참조 반환"""
    try:
        db = get_firestore_client()
        return db.collection("sessions").document(session_id).collection("messages")
    except Exception as e:
        print(f"Firestore 연결 실패, 메모리 fallback 사용: {e}")
        return None


async def save_message(
    session_id: str,
    message_id: str,
    role: str,
    content: str,
    metadata: Optional[Dict] = None
) -> bool:
    """
    메시지 저장

    Args:
        session_id: 세션 ID
        message_id: 메시지 ID
        role: "user" 또는 "assistant"
        content: 메시지 내용
        metadata: 추가 메타데이터

    Returns:
        성공 여부
    """
    message_data = {
        "message_id": message_id,
        "role": role,
        "content": content,
        "timestamp": datetime.now().isoformat(),
        "metadata": metadata or {}
    }

    collection = _get_messages_collection(session_id)

    if collection is not None:
        try:
            collection.document(message_id).set(message_data)
            return True
        except Exception as e:
            print(f"Firestore 저장 실패: {e}")

    # Fallback: 메모리 저장
    if session_id not in _memory_fallback:
        _memory_fallback[session_id] = []
    _memory_fallback[session_id].append(message_data)
    return True


async def get_messages(session_id: str) -> List[Dict]:
    """
    세션의 모든 메시지 조회

    Args:
        session_id: 세션 ID

    Returns:
        메시지 리스트 (시간순 정렬)
    """
    collection = _get_messages_collection(session_id)

    if collection is not None:
        try:
            docs = collection.order_by("timestamp").stream()
            return [doc.to_dict() for doc in docs]
        except Exception as e:
            print(f"Firestore 조회 실패: {e}")

    # Fallback: 메모리 조회
    return _memory_fallback.get(session_id, [])


async def init_session_messages(session_id: str, first_message: Dict) -> bool:
    """
    세션 시작 시 첫 메시지 저장

    Args:
        session_id: 세션 ID
        first_message: 첫 번째 메시지 dict

    Returns:
        성공 여부
    """
    return await save_message(
        session_id=session_id,
        message_id=first_message.get("message_id", f"msg_{session_id[:8]}"),
        role=first_message.get("role", "assistant"),
        content=first_message.get("content", ""),
        metadata=first_message.get("metadata")
    )


async def append_user_message(
    session_id: str,
    message_id: str,
    content: str
) -> bool:
    """사용자 메시지 추가"""
    return await save_message(
        session_id=session_id,
        message_id=message_id,
        role="user",
        content=content
    )


async def append_assistant_message(
    session_id: str,
    message_id: str,
    content: str,
    metadata: Optional[Dict] = None
) -> bool:
    """AI 응답 메시지 추가"""
    return await save_message(
        session_id=session_id,
        message_id=message_id,
        role="assistant",
        content=content,
        metadata=metadata
    )
