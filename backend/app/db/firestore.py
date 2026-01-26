import os
import logging
from typing import Optional
from pathlib import Path
from google.cloud import firestore

logger = logging.getLogger(__name__)

class FirestoreClient:
    _instance = None
    _client: Optional[firestore.Client] = None

    @classmethod
    def get_client(cls) -> Optional[firestore.Client]:
        if cls._client:
            return cls._client
        
        # Initialize if not already initialized
        try:
            # Try to find the key file
            base_dir = Path(__file__).resolve().parents[2] # backend/
            key_path = base_dir / "knu-team-03-e43bba38b267.json"
            
            if key_path.exists():
                os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(key_path)
                logger.info(f"🔑 키 파일을 찾았습니다: {key_path}")
            
            cls._client = firestore.Client()
            logger.info("✅ Firestore 연결 완료")
            return cls._client
        except Exception as e:
            logger.warning(f"⚠️ Firestore 연결 실패: {e}")
            return None

def get_db() -> Optional[firestore.Client]:
    return FirestoreClient.get_client()
