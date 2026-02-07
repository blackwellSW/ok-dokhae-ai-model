import traceback
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    # --------------------------------------------------------------------------------
    # 정상 애플리케이션 로직
    # --------------------------------------------------------------------------------
    from app.api.auth import router as auth_router
    from app.api.chat_learning import router as chat_router
    from app.api.classical_literature import router as classical_literature_router
    from app.api.learning_system import router as learning_system_router
    from app.api.report_generator_api import router as report_router
    from app.api.documents import router as documents_router
    from app.api.sessions import router as sessions_router
    from app.api.teacher import router as teacher_router

    app = FastAPI(
        title="OK독해 AI 학습 시스템",
        description="""
        ## 🎓 고전문학 사고유도 대화 AI + 자동 평가 시스템
        
        ### 핵심 기능
        
        #### 🔐 인증 시스템 (Authentication)
        - 회원가입 / 로그인 (JWT)
        - Google OAuth 지원
        - 사용자 유형: 학생(student), 교사(teacher), 관리자(admin)
        
        #### 📄 문서 관리 (Document Management) - **NEW**
        - 문서 업로드 (PDF/TXT/DOCX)
        - 텍스트 추출 및 청크 분할
        - 프리뷰 및 청크 조회
        
        #### 📚 세션 관리 (Session Management) - **NEW**
        - 학습 세션 생성/조회
        - 대화 로그 저장 및 조회
        - 세션 종료 및 리포트 생성
        
        #### 💬 채팅 학습 (Chat Learning)
        - 소크라틱 대화형 학습
        - 실시간 피드백 및 평가
        - 4턴 핑퐁 시스템
        
        #### 📊 리포트 관리 (Report Management) - **ENHANCED**
        - 리포트 생성 및 저장
        - 리포트 재조회 (GET /reports/{id})
        - 근거(citation) 표준 스키마
        
        #### 👩‍🏫 교사 허브 (Teacher Hub) - **NEW**
        - 학생 목록 조회
        - 학생별 세션/요약 조회
        - 대시보드 (실시간 현황)
        
        #### 📚 고전문학 AI (Classical Literature)
        - 사고유도 대화 생성
        - 통합 평가 (질적 70% + 정량 30%)
        
        #### 🎯 고급 학습 시스템 (Advanced)
        - Thinking Path Engine
        - 동적 질문 생성
        
        ---
        ### 사용 흐름 (Frontend 가이드)
        
        1. **인증**: `POST /auth/google-login` 또는 `POST /auth/login`
        2. **문서 업로드**: `POST /documents` → document_id 받음
        3. **세션 시작**: `POST /sessions` → session_id + 첫 질문 받음
        4. **대화 진행**: `POST /sessions/{id}/messages` (4턴 반복)
        5. **리포트 조회**: `GET /reports/{id}`
        
        교사용: `GET /teacher/*` 엔드포인트 활용
        """,
        version="5.0.0"
    )

    # CORS 설정 (프론트엔드 연동 대비)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 라우터 등록
    app.include_router(auth_router)  # 인증
    app.include_router(documents_router)  # 문서 관리 (NEW)
    app.include_router(sessions_router)  # 세션 관리 (NEW)
    app.include_router(report_router)  # 리포트 관리
    app.include_router(teacher_router)  # 교사 허브 (NEW)
    app.include_router(chat_router)  # 채팅 학습 (레거시)
    app.include_router(classical_literature_router)  # 고전문학 AI
    app.include_router(learning_system_router)  # 고급 학습 시스템

    @app.get("/")
    async def root():
        return {
            "message": "OK독해 AI 학습 시스템이 실행 중입니다.",
            "version": "5.0.0",
            "status": "operational",
            "features": [
                "📄 Document Upload & Parsing",
                "📚 Session Management",
                "📊 Report Generation & Retrieval",
                "👩‍🏫 Teacher Hub",
                "💬 Chat Learning",
                "🎯 Thinking Path Engine"
            ]
        }

except Exception as e:
    # --------------------------------------------------------------------------------
    # FAIL-SAFE 모드: 시작 중 에러 발생 시 에러 내용을 반환하는 앱 실행
    # --------------------------------------------------------------------------------
    error_msg = traceback.format_exc()
    print(f"CRITICAL STARTUP ERROR:\n{error_msg}", file=sys.stderr)
    
    app = FastAPI(title="Startup Error Mode")
    
    @app.get("/")
    @app.get("/{full_path:path}")
    async def error_root(full_path: str = ""):
        return {
            "status": "error",
            "message": "Application failed to start.",
            "error_detail": error_msg.splitlines()
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)



