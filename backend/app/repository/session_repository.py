"""
session_repository.py
역할: Google Cloud Firestore를 이용한 학습 세션 데이터의 안정적인 CRUD 작업 담당.
"""

from typing import Dict, Any, Optional
from google.cloud import firestore
from google.api_core.exceptions import (
    NotFound,
    AlreadyExists,
    GoogleAPICallError
)


class SessionRepository:
    """
    Firestore 'study_sessions' 컬렉션에 대한 데이터 접근 레이어.
    안정성을 위해 명시적인 존재 여부 확인 및 구체적인 예외 처리를 수행합니다.
    """

    def __init__(self):
        # Firestore 클라이언트는 싱글톤 패턴으로 관리됨
        self.db = firestore.Client()
        self.collection_name = "study_sessions"

    def create_session(self, session_id: str, data: Dict[str, Any]) -> None:
        """
        새로운 학습 세션 문서를 생성합니다. 
        동일한 ID가 이미 존재하는 경우 의도치 않은 덮어쓰기 방지를 위해 예외를 발생시킵니다.
        
        Args:
            session_id: 세션 고유 ID
            data: 저장할 세션 데이터
        Raises:
            ConflictError (ValueError): 동일한 ID의 세션이 이미 존재하는 경우
            RuntimeError: Firestore 통신 에러 발생 시
        """
        try:
            doc_ref = self.db.collection(self.collection_name).document(session_id)
            # .create()는 문서가 이미 존재하면 AlreadyExists 예외를 발생시킴
            doc_ref.create(data)
        except AlreadyExists:
            raise ValueError(f"Session with ID '{session_id}' already exists. Overwrite prevented.")
        except GoogleAPICallError as e:
            raise RuntimeError(f"Cloud API error during session creation: {str(e)}")

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        ID를 기준으로 세션 문서를 단건 조회합니다.
        
        Args:
            session_id: 조회할 세션 고유 ID
        Returns:
            Optional[Dict[str, Any]]: 문서 데이터 혹은 존재하지 않을 경우 None
        Raises:
            RuntimeError: Firestore 통신 에러 발생 시
        """
        try:
            doc_ref = self.db.collection(self.collection_name).document(session_id)
            doc = doc_ref.get()
            if doc.exists:
                return doc.to_dict()
            return None
        except GoogleAPICallError as e:
            raise RuntimeError(f"Cloud API error during session lookup: {str(e)}")

    def update_session(self, session_id: str, update_data: Dict[str, Any]) -> None:
        """
        기존 세션 문서의 데이터를 부분 업데이트합니다.
        업데이트 전 문서 존재 여부를 명시적으로 확인하여 예외를 처분합니다.
        
        Args:
            session_id: 업데이트할 세션 고유 ID
            update_data: 업데이트할 필드 데이터
        Raises:
            ValueError: 존재하지 않는 세션인 경우
            RuntimeError: Firestore 통신 에러 발생 시
        """
        try:
            doc_ref = self.db.collection(self.collection_name).document(session_id)
            
            # 업데이트 전 명시적으로 존재 여부 확인
            doc = doc_ref.get()
            if not doc.exists:
                raise ValueError(f"Cannot update. Session with ID '{session_id}' does not exist.")
            
            doc_ref.update(update_data)
        except NotFound:
            # get()과 update() 사이의 극히 짧은 시간에 문서가 삭제된 경우 대응
            raise ValueError(f"Session with ID '{session_id}' was not found during update.")
        except GoogleAPICallError as e:
            raise RuntimeError(f"Cloud API error during session update: {str(e)}")


# 싱글톤 인스턴스 생성
session_repo = SessionRepository()
