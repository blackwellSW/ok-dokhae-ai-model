
from typing import Dict, Any, Optional, List
from app.db.firestore import FirestoreRepository
from datetime import datetime
from app.schemas.learning import LearningState, ThinkingLog

class SessionRepository(FirestoreRepository):
    """
    Manages user sessions (LearningStates in this context, or actual sessions if distinct).
    Based on models.py, 'LearningState' seems to be the main session tracker.
    But there is also 'study_sessions' collection in the original repo query?
    The original repo used 'study_sessions' collection name.
    Let's stick to 'learning_states' for consistency with models, or map it.
    """
    def __init__(self):
        super().__init__("learning_states")
        self.log_repo = FirestoreRepository("thinking_logs")

    async def create_session(self, state_data: Dict[str, Any]) -> LearningState:
        state_data["created_at"] = datetime.utcnow().isoformat()
        state_data["updated_at"] = datetime.utcnow().isoformat()
        await self.create(state_data["state_id"], state_data)
        return LearningState(**state_data)

    async def get_session(self, state_id: str) -> Optional[LearningState]:
        data = await self.get(state_id)
        return LearningState(**data) if data else None

    async def update_session(self, state_id: str, update_data: Dict[str, Any]) -> Optional[LearningState]:
        update_data["updated_at"] = datetime.utcnow().isoformat()
        data = await self.update(state_id, update_data)
        return LearningState(**data) if data else None

    async def create_log(self, log_data: Dict[str, Any]) -> ThinkingLog:
        log_data["created_at"] = datetime.utcnow().isoformat()
        await self.log_repo.create(log_data["log_id"], log_data)
        return ThinkingLog(**log_data)

    async def get_logs_by_state(self, state_id: str) -> List[ThinkingLog]:
        logs = await self.log_repo.query("state_id", "==", state_id)
        # Sort by creation time if needed
        logs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return [ThinkingLog(**log) for log in logs]
    
    async def get_active_session_by_user(self, user_id: str) -> Optional[LearningState]:
        sessions = await self.query("user_id", "==", user_id)
        # Filter for ACTIVE locally or via composite query if index exists
        active_sessions = [s for s in sessions if s.get("status") == "ACTIVE"]
        # Return most recent one
        if active_sessions:
            active_sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
            return LearningState(**active_sessions[0])
        return None

    async def get_sessions_by_user(self, user_id: str, status: Optional[str] = None, days: int = 30) -> List[LearningState]:
        # Basic query by user_id
        sessions_data = await self.query("user_id", "==", user_id)
        
        # In-memory filtering for status and date
        # Note: In production with large data, validation of composite indexes is needed for server-side filtering.
        filtered_sessions = []
        cutoff = None
        if days:
            from datetime import datetime, timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)
            cutoff_iso = cutoff.isoformat()

        for s in sessions_data:
            # Status filter
            if status and s.get("status") != status:
                continue
            
            # Date filter
            created_at = s.get("created_at")
            if cutoff_iso and created_at and created_at < cutoff_iso:
                continue
            
            filtered_sessions.append(LearningState(**s))
            
        # Sort by updated_at desc
        filtered_sessions.sort(key=lambda x: x.updated_at, reverse=True)
        return filtered_sessions

# 싱글톤 인스턴스 (다른 모듈에서 import하여 사용)
session_repo = SessionRepository()
