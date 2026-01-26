import os
import sys
import logging
from pathlib import Path
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from google.cloud import firestore

# [1] 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# [2] 전역 변수 (나중에 로드)
db = None
analyzer = None
evaluator = None

# [3] 경로 및 임포트 최적화
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/ directory
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

try:
    from app.logic.analyzer import LogicAnalyzer
    from app.logic.evaluator import Evaluator
    logger.info("✅ 엔진 모듈 임포트 성공")
except ImportError as e:
    logger.error(f"❌ 엔진 모듈 임포트 실패: {e}")
    # Docker/Production 환경 대비
    try:
        from .logic.analyzer import LogicAnalyzer
        from .logic.evaluator import Evaluator
    except ImportError:
        raise e

# [4] 서버 생명주기 관리 (Lazy Loading)
@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, analyzer, evaluator
    
    logger.info("🚀 [STARTUP] 인프라 초기화 시작...")
    
    # 1. Firestore 설정
    KEY_NAME = "knu-team-03-e43bba38b267.json" 
    KEY_PATH = BASE_DIR / KEY_NAME

    if KEY_PATH.exists():
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(KEY_PATH)
        logger.info(f"🔑 키 파일을 찾았습니다: {KEY_PATH}")
    else:
        logger.error(f"⚠️ 키 파일 누락! Firestore 연결이 제한될 수 있습니다.")

    try:
        db = firestore.Client()
        # 간단한 연결 테스트
        db.collection("health_check").document("last_startup").set({
            "status": "online",
            "timestamp": firestore.SERVER_TIMESTAMP
        })
        logger.info("✅ Firestore 연결 확인")
    except Exception as e:
        logger.warning(f"⚠️ Firestore 연결 실패(무시하고 진행): {e}")

    # 2. 무거운 AI 모델 로드 (서버가 응답 가능한 상태가 된 후 실행)
    logger.info("🧠 AI 엔진(4.5GB) 로드 시작... (이 과정은 로그에서만 확인 가능)")
    try:
        analyzer = LogicAnalyzer()
        evaluator = Evaluator()
        logger.info("✅ AI 엔진 로드 완료! 이제 분석이 가능합니다.")
    except Exception as e:
        logger.error(f"❌ AI 엔진 로드 실패: {e}")
        
    yield
    logger.info("🛑 서버 종료 중...")

# [5] FastAPI 앱 초기화
app = FastAPI(
    title="OK-DOK-HAE API Server",
    lifespan=lifespan
)

# [6] 데이터 규격
class AnalyzeRequest(BaseModel):
    user_id: str = Field(..., example="yongbin_choi")
    session_id: str = Field(..., example="sess_20260123_01")
    text: str = Field(..., description="분석할 비문학 원문")

# [7] API 엔드포인트
@app.get("/", tags=["Health"])
async def root():
    # 모델 로드 상태를 함께 반환해서 팀원들이 확인할 수 있게 함
    status = "ready" if analyzer else "loading"
    return {"status": status, "message": "OK-DOK-HAE API is online"}

@app.post("/analyze", tags=["독해 엔진"])
async def analyze_text(req: AnalyzeRequest):
    if analyzer is None:
        raise HTTPException(status_code=503, detail="AI 엔진이 로딩 중입니다. 1~2분 후 다시 시도해 주세요.")
    
    try:
        nodes = analyzer.analyze(req.text)
        # Firestore 저장 로직 (선택 사항)
        if db:
            db.collection("analysis_logs").add({
                "user_id": req.user_id,
                "text_length": len(req.text),
                "created_at": firestore.SERVER_TIMESTAMP
            })
        return {"nodes": nodes}
    except Exception as e:
        logger.error(f"분석 오류: {e}")
        raise HTTPException(status_code=500, detail="엔진 분석 중 오류 발생")