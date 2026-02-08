from typing import Optional, List, Dict, Any
from app.db.firestore import FirestoreRepository
from datetime import datetime

class ReportRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("reports")

    async def create_report(self, report_data: dict) -> dict:
        doc_id = report_data.get("report_id")
        if not doc_id:
            import uuid
            doc_id = f"rpt_{uuid.uuid4().hex[:12]}"
            report_data["report_id"] = doc_id
        
        # Ensure timestamp
        if "created_at" not in report_data:
            report_data["created_at"] = datetime.utcnow().isoformat()
            
        await self.create(doc_id, report_data)
        return report_data

    async def get_report(self, report_id: str) -> Optional[dict]:
        return await self.get(report_id)

    async def get_reports_by_user(self, user_id: str, days: int = 30) -> List[dict]:
        # Firestore query for reports by user
        # Depending on FirestoreRepository implementation, we might need a composite index for equality + range
        # For now, simple query by user and in-memory filter if needed, or query by user only if too complex
        
        params = [("user_id", "==", user_id)]
        reports = await self.query_by_multiple(params)
        
        # Filter by date in memory if needed (or if repository supports range)
        if days:
            from datetime import timedelta
            cutoff = datetime.utcnow() - timedelta(days=days)
            filtered = []
            for r in reports:
                created_at = r.get("created_at")
                if created_at:
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", ""))
                        # Simple naive check
                        if dt >= cutoff:
                            filtered.append(r)
                    except:
                        filtered.append(r) # Include if date parse fails
            return sorted(filtered, key=lambda x: x.get("created_at", ""), reverse=True)
            
        return sorted(reports, key=lambda x: x.get("created_at", ""), reverse=True)

report_repo = ReportRepository()
