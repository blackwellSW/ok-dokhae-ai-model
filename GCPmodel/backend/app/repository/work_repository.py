
from typing import List, Optional
from app.db.firestore import FirestoreRepository
from datetime import datetime
from app.schemas.work import LiteraryWork, TextChunk, LiteraryWorkCreate, TextChunkCreate

class WorkRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("literary_works")
        self.chunk_repo = FirestoreRepository("text_chunks")

    async def create_work(self, work: LiteraryWorkCreate) -> LiteraryWork:
        work_data = work.model_dump()
        work_data["created_at"] = datetime.utcnow().isoformat()
        work_data["updated_at"] = datetime.utcnow().isoformat()
        
        await self.create(work.work_id, work_data)
        return LiteraryWork(**work_data)

    async def get_work(self, work_id: str) -> Optional[LiteraryWork]:
        data = await self.get(work_id)
        return LiteraryWork(**data) if data else None

    async def list_works(self, limit: int = 100) -> List[LiteraryWork]:
        data_list = await self.list_all(limit)
        return [LiteraryWork(**data) for data in data_list]

    async def create_chunk(self, chunk: TextChunkCreate) -> TextChunk:
        chunk_data = chunk.model_dump()
        chunk_data["created_at"] = datetime.utcnow().isoformat()
        
        await self.chunk_repo.create(chunk.chunk_id, chunk_data)
        return TextChunk(**chunk_data)

    async def get_chunks_by_work(self, work_id: str) -> List[TextChunk]:
        # Note: Firestore queries require composite indexes for advanced filtering.
        # Simple equality is fine.
        chunks_data = await self.chunk_repo.query("work_id", "==", work_id)
        # Sort by sequence manually since we might not have index
        chunks_data.sort(key=lambda x: x.get("sequence", 0))
        return [TextChunk(**data) for data in chunks_data]
