import logging
import sys
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from app.api.inference import router as inference_router
from app.services.inference_service import InferenceService
from app.db.firestore import get_db

# [1] 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# [2] 경로 설정
BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# [3] 서버 생명주기
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 [STARTUP] Server initializing...")
    
    # 1. DB Check
    db = get_db()
    if db:
        logger.info("✅ DB Connected.")
    else:
        logger.warning("⚠️ DB Connection Failed.")

    # 2. Preload Models (Optional - can be lazy loaded via service)
    # InferenceService.load_models() 
    
    yield
    logger.info("🛑 [SHUTDOWN] Server stopping...")

# [4] FastAPI 앱 초기화
app = FastAPI(
    title="OK-DOK-HAE API Server",
    version="2.0.0",
    description="Refactored API with Layered Architecture",
    lifespan=lifespan
)

# [5] 라우터 등록
app.include_router(inference_router, prefix="/api/v1")

@app.get("/", tags=["Health"])
async def root():
    return {"status": "online", "version": "2.0.0"}
