from typing import List, Dict, Optional
import uuid

class SessionManager:
    """
    사용자의 독해 세션 상태를 관리합니다.
    (메모리 기반 - 운영 환경에서는 Redis/DB 권장)
    """
    def __init__(self):
        self.sessions = {}

    def create_session(self, nodes: List[Dict]) -> str:
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "nodes": nodes,
            "key_nodes": [n for n in nodes if n["is_key_node"]],
            "current_node_idx": 0,
            "history": [],
            "completed": False
        }
        return session_id

    def get_session(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)

    def update_session(self, session_id: str, feedback: str):
        if session_id in self.sessions:
            self.sessions[session_id]["history"].append(feedback)

    def move_to_next_node(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if not session:
            return False
            
        session["current_node_idx"] += 1
        if session["current_node_idx"] >= len(session["key_nodes"]):
            session["completed"] = True
            return False
        return True
