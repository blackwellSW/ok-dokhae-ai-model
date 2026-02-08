"""
Firebase Admin SDK 초기화
역할: Firebase Auth 토큰 검증 및 Firestore 클라이언트 제공

사용 방법:
1. GCP에서 서비스 계정 키 생성 (Firebase Admin SDK 권한 필요)
2. GOOGLE_APPLICATION_CREDENTIALS 환경변수로 키 파일 경로 설정
   또는 Cloud Run에서는 자동으로 기본 서비스 계정 사용
"""

import os
from typing import Optional
import firebase_admin
from firebase_admin import credentials, auth, firestore

# Firebase 앱 인스턴스 (싱글톤)
_firebase_app: Optional[firebase_admin.App] = None
_firestore_client = None


def initialize_firebase() -> firebase_admin.App:
    """
    Firebase Admin SDK 초기화

    Cloud Run에서는 기본 서비스 계정을 자동으로 사용합니다.
    로컬 개발 시에는 GOOGLE_APPLICATION_CREDENTIALS 환경변수 설정 필요.
    """
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    try:
        # 이미 초기화되었는지 확인
        _firebase_app = firebase_admin.get_app()
    except ValueError:
        # 초기화되지 않았으면 새로 초기화
        # Cloud Run에서는 기본 자격 증명 사용
        # 로컬에서는 GOOGLE_APPLICATION_CREDENTIALS 환경변수 필요
        cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if cred_path and os.path.exists(cred_path):
            cred = credentials.Certificate(cred_path)
            _firebase_app = firebase_admin.initialize_app(cred)
        else:
            # Cloud Run 또는 GCE에서 기본 자격 증명 사용
            _firebase_app = firebase_admin.initialize_app()

        print("Firebase Admin SDK initialized successfully")

    return _firebase_app


def get_firestore_client():
    """
    Firestore 클라이언트 반환 (싱글톤)

    사용 예시:
    ```python
    from app.core.firebase import get_firestore_client

    db = get_firestore_client()
    doc_ref = db.collection("sessions").document(session_id)
    doc_ref.set({"messages": [...]})
    ```
    """
    global _firestore_client

    if _firestore_client is None:
        initialize_firebase()
        _firestore_client = firestore.client()

    return _firestore_client


async def verify_firebase_token(id_token: str) -> Optional[dict]:
    """
    Firebase ID Token 검증

    Args:
        id_token: 프론트엔드에서 받은 Firebase ID Token

    Returns:
        성공 시: 사용자 정보 dict (uid, email, name 등)
        실패 시: None

    사용 예시:
    ```python
    user_info = await verify_firebase_token(request.id_token)
    if not user_info:
        raise HTTPException(status_code=401, detail="Invalid token")
    ```
    """
    try:
        initialize_firebase()
        decoded_token = auth.verify_id_token(id_token)

        return {
            "uid": decoded_token.get("uid"),
            "email": decoded_token.get("email"),
            "name": decoded_token.get("name", decoded_token.get("email", "").split("@")[0]),
            "email_verified": decoded_token.get("email_verified", False),
            "picture": decoded_token.get("picture"),
            "provider": decoded_token.get("firebase", {}).get("sign_in_provider", "unknown"),
        }
    except auth.InvalidIdTokenError:
        print("Invalid Firebase ID token")
        return None
    except auth.ExpiredIdTokenError:
        print("Expired Firebase ID token")
        return None
    except Exception as e:
        print(f"Firebase token verification error: {e}")
        return None


def get_user_by_email(email: str) -> Optional[dict]:
    """
    이메일로 Firebase 사용자 조회

    Args:
        email: 사용자 이메일

    Returns:
        성공 시: 사용자 정보 dict
        실패 시: None
    """
    try:
        initialize_firebase()
        user = auth.get_user_by_email(email)
        return {
            "uid": user.uid,
            "email": user.email,
            "name": user.display_name,
            "email_verified": user.email_verified,
            "disabled": user.disabled,
        }
    except auth.UserNotFoundError:
        return None
    except Exception as e:
        print(f"Error getting user by email: {e}")
        return None
