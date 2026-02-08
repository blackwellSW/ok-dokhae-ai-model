
from typing import List, Optional
from app.db.firestore import FirestoreRepository
from datetime import datetime
from app.schemas.document import RAGDocument, RAGDocumentCreate

class DocumentRepository(FirestoreRepository):
    def __init__(self):
        super().__init__("rag_documents")

    async def create_document(self, doc: RAGDocumentCreate) -> RAGDocument:
        doc_data = doc.model_dump()
        doc_data["created_at"] = datetime.utcnow().isoformat()
        
        await self.create(doc.doc_id, doc_data)
        return RAGDocument(**doc_data)

    async def get_document(self, doc_id: str) -> Optional[RAGDocument]:
        data = await self.get(doc_id)
        return RAGDocument(**data) if data else None

    async def list_documents(self, limit: int = 100) -> List[RAGDocument]:
        data_list = await self.list_all(limit)
        return [RAGDocument(**data) for data in data_list]
    
    async def get_documents_by_type(self, doc_type: str) -> List[RAGDocument]:
        data_list = await self.query("doc_type", "==", doc_type)
        return [RAGDocument(**data) for data in data_list]
