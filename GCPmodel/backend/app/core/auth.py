"""
인증 관련 유틸리티
역할: JWT 토큰 생성, 비밀번호 해싱, 인증 검증

지원하는 인증 방식:
1. Firebase Auth (권장) - Firebase SDK에서 받은 ID Token 검증
2. Google OAuth (레거시) - 직접 Google OAuth로 받은 ID Token 검증
"""

from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.config import get_settings
# from app.db.session import get_db  # Removed
# from app.db.models import User  # Removed
from app.schemas.user import User  # New Pydantic Model
from app.repository.user_repository import UserRepository

# Firebase Auth (선호)
from app.core.firebase import verify_firebase_token

# Google OAuth (fallback)
from google.oauth2 import id_token
from google.auth.transport import requests

settings = get_settings()

# 비밀번호 해싱 (Google 로그인 사용 시 비밀번호는 불필요하지만 호환성을 위해 유지)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 설정
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# JWT 설정 (별도의 시크릿 키 사용)
SECRET_KEY = settings.JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간


async def verify_id_token_universal(token: str) -> Optional[dict]:
    """
    ID Token 검증 (Firebase 우선, Google OAuth fallback)

    프론트엔드가 Firebase SDK로 전환되면 Firebase 검증 사용.
    아직 전환 전이면 기존 Google OAuth 검증으로 fallback.

    Returns:
        성공 시: {"email": ..., "name": ..., "sub": ...}
        실패 시: None
    """
    # 1. Firebase Auth 시도 (권장)
    firebase_user = await verify_firebase_token(token)
    if firebase_user:
        return {
            "email": firebase_user.get("email"),
            "name": firebase_user.get("name"),
            "sub": firebase_user.get("uid"),
            "provider": "firebase"
        }

    # 2. Google OAuth fallback (레거시)
    google_user = await verify_google_token(token)
    if google_user:
        return {
            "email": google_user.get("email"),
            "name": google_user.get("name"),
            "sub": google_user.get("sub"),
            "provider": "google"
        }

    return None


async def verify_google_token(token: str) -> Optional[dict]:
    """Google ID Token 검증 및 정보 추출 (레거시)"""
    try:
        id_info = id_token.verify_oauth2_token(
            token,
            requests.Request(),
            settings.GOOGLE_CLIENT_ID
        )
        return id_info
    except ValueError:
        return None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호 해싱 (bcrypt 72바이트 제한 적용)"""
    # bcrypt는 72바이트까지만 지원하므로 truncate
    password_bytes = password.encode('utf-8')[:72]
    return pwd_context.hash(password_bytes.decode('utf-8', errors='ignore'))


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> User:
    """현재 로그인한 사용자 조회"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보를 확인할 수 없습니다",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    # DB에서 사용자 조회 (Firestore)
    repository = UserRepository()
    user_data = await repository.get_by_user_id(user_id)
    
    if user_data is None:
        raise credentials_exception
    
    # Convert dict to Pydantic model
    user = User(**user_data)
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )
    
    return user


async def get_current_active_student(
    current_user: User = Depends(get_current_user)
) -> User:
    """학생 권한 확인"""
    if current_user.user_type not in ["student", "teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="학생 권한이 필요합니다"
        )
    return current_user


async def get_current_teacher(
    current_user: User = Depends(get_current_user)
) -> User:
    """교사 권한 확인"""
    if current_user.user_type not in ["teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="교사 권한이 필요합니다"
        )
    return current_user


async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """관리자 권한 확인"""
    if current_user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다"
        )
    return current_user
