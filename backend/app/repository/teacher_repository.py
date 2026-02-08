
from typing import Dict, Any, Optional, List
from app.db.firestore import FirestoreRepository
from datetime import datetime
from app.schemas.learning import TeacherDashboardData

class TeacherRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("teacher_dashboard_data")

    async def get_dashboard(self, dashboard_id: str) -> Optional[TeacherDashboardData]:
        data = await self.get(dashboard_id)
        return TeacherDashboardData(**data) if data else None

    async def get_dashboard_by_teacher(self, teacher_id: str) -> Optional[TeacherDashboardData]:
        dashboards = await self.query("teacher_id", "==", teacher_id)
        if dashboards:
            return TeacherDashboardData(**dashboards[0])
        return None

    async def create_dashboard(self, dashboard_data: Dict[str, Any]) -> TeacherDashboardData:
        dashboard_data["updated_at"] = datetime.utcnow().isoformat()
        await self.create(dashboard_data["dashboard_id"], dashboard_data)
        return TeacherDashboardData(**dashboard_data)

    async def update_dashboard(self, dashboard_id: str, update_data: Dict[str, Any]) -> Optional[TeacherDashboardData]:
        update_data["updated_at"] = datetime.utcnow().isoformat()
        data = await self.update(dashboard_id, update_data)
        return TeacherDashboardData(**data) if data else None
