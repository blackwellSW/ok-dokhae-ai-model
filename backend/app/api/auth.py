"""
인증 API
역할: 회원가입, 로그인, 사용자 정보 조회
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.db.session import get_db
from app.db.models import User
from app.core.auth import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_user,
    verify_google_token
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ============================================================
# Request/Response Models
# ============================================================

class GoogleLoginRequest(BaseModel):
    """Google 로그인 요청"""
    id_token: str
    user_type: str = "student"  # 기본값 student


class UserRegisterRequest(BaseModel):
    """회원가입 요청 (Legacy)"""
    email: EmailStr
    password: str
    username: str
    user_type: str  # student, teacher, admin


class UserRegisterResponse(BaseModel):
    """회원가입 응답"""
    user_id: str
    email: str
    username: str
    user_type: str
    message: str


class TokenResponse(BaseModel):
    """로그인 응답"""
    access_token: str
    token_type: str
    user_id: str
    username: str
    user_type: str


class UserInfoResponse(BaseModel):
    """사용자 정보 응답"""
    user_id: str
    email: str
    username: str
    user_type: str
    is_active: bool
    created_at: str


# ============================================================
# API Endpoints
# ============================================================

@router.post("/google-login", response_model=TokenResponse)
async def google_login(
    request: GoogleLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Google 계정으로 로그인/회원가입
    
    1. 프론트엔드에서 Google 로그인 후 받은 id_token을 전달
    2. 토큰 검증 및 사용자 정보 추출
    3. DB에 없으면 자동 회원가입
    4. JWT 액세스 토큰 발급
    """
    
    # 1. Google Token 검증 (현재는 Client ID 미설정 시에도 테스트 가능하도록 skip 로직 고려 가능하지만 정석대로 구현)
    # 실제 운영 시에는 config.py의 GOOGLE_CLIENT_ID가 정확해야 함
    google_user_info = await verify_google_token(request.id_token)
    
    if not google_user_info:
        # 개발 편의를 위해 토큰이 "TEST_TOKEN"인 경우 테스트 유저로 통과 (삭제 가능)
        if request.id_token == "TEST_TOKEN":
             google_user_info = {
                 "email": "test@example.com", 
                 "name": "Test User", 
                 "sub": "test_google_id"
             }
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 Google 토큰입니다"
            )
    
    email = google_user_info.get("email")
    username = google_user_info.get("name")
    
    # 2. 사용자 조회 또는 생성
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        # 신규 회원가입
        user = User(
            user_id=str(uuid.uuid4()),
            email=email,
            hashed_password="",  # Google 로그인 유저는 비밀번호 없음
            username=username,
            user_type=request.user_type,
            is_active=True,
            is_verified=True, # 구글 인증이므로 verified
            profile_data={"google_sub": google_user_info.get("sub")}
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # 3. 자체 JWT 토큰 발급
    access_token = create_access_token(
        data={"sub": user.user_id, "user_type": user.user_type}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        username=user.username,
        user_type=user.user_type
    )


@router.post("/register", response_model=UserRegisterResponse)
async def register(
    request: UserRegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    회원가입
    
    - student: 학생
    - teacher: 교사
    - admin: 관리자
    """
    
    # 이메일 중복 확인
    stmt = select(User).where(User.email == request.email)
    result = await db.execute(stmt)
    existing_user = result.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="이미 등록된 이메일입니다"
        )
    
    # 사용자 유형 검증
    if request.user_type not in ["student", "teacher", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 사용자 유형입니다. (student, teacher, admin 중 선택)"
        )
    
    # 사용자 생성
    user = User(
        user_id=str(uuid.uuid4()),
        email=request.email,
        hashed_password=get_password_hash(request.password),
        username=request.username,
        user_type=request.user_type,
        is_active=True,
        is_verified=False,
        profile_data={}
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    return UserRegisterResponse(
        user_id=user.user_id,
        email=user.email,
        username=user.username,
        user_type=user.user_type,
        message="회원가입이 완료되었습니다"
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    로그인
    
    - username: 이메일 주소
    - password: 비밀번호
    """
    
    # 사용자 조회 (이메일로)
    stmt = select(User).where(User.email == form_data.username)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 비밀번호 확인
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 활성 계정 확인
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="비활성화된 계정입니다"
        )
    
    # JWT 토큰 생성
    access_token = create_access_token(
        data={"sub": user.user_id, "user_type": user.user_type}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.user_id,
        username=user.username,
        user_type=user.user_type
    )


@router.get("/me", response_model=UserInfoResponse)
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    현재 로그인한 사용자 정보 조회
    
    헤더에 Authorization: Bearer {token} 필요
    """
    
    return UserInfoResponse(
        user_id=current_user.user_id,
        email=current_user.email,
        username=current_user.username,
        user_type=current_user.user_type,
        is_active=current_user.is_active,
        created_at=current_user.created_at.isoformat()
    )


@router.get("/health")
async def auth_health():
    """인증 시스템 헬스 체크"""
    return {
        "status": "healthy",
        "features": ["register", "login", "JWT authentication"]
    }
