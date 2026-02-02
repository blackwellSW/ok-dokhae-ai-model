"""
main.py
역할: FastAPI 애플리케이션 초기화 및 서버 통합 관리.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.study_sessions import router as study_sessions_router
from app.api.evaluation_controller import router as evaluation_router

app = FastAPI(
    title="AI 학습 시스템 백엔드",
    description="Stage-Gate-Branch 기반 학습 흐름 통제 시스템",
    version="1.0.0"
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
app.include_router(study_sessions_router)
app.include_router(evaluation_router)

@app.get("/")
async def root():
    return {"message": "AI Learning System Backend is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
