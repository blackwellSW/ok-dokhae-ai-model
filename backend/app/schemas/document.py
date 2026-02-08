
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class RAGDocumentBase(BaseModel):
    doc_id: str
    doc_type: str
    work_id: Optional[str] = None
    chunk_id: Optional[str] = None
    content: str
    embedding: Optional[Dict] = None
    usage_stages: List[str] = []
    priority: int = 5

class RAGDocumentCreate(RAGDocumentBase):
    pass

class RAGDocument(RAGDocumentBase):
    created_at: str
