"""
콘텐츠 관리 서비스
역할: 작품/지문 관리, RAG 문서 인덱싱
"""

import uuid
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.models import LiteraryWork, TextChunk, RAGDocument


class ContentManager:
    """콘텐츠 관리자"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_work(
        self,
        title: str,
        author: str,
        period: str,
        difficulty: int,
        genre: str,
        description: str = "",
        keywords: Dict = None
    ) -> str:
        """작품 등록"""
        
        work = LiteraryWork(
            work_id=str(uuid.uuid4()),
            title=title,
            author=author,
            period=period,
            difficulty=difficulty,
            genre=genre,
            description=description,
            keywords=keywords or {}
        )
        
        self.db.add(work)
        await self.db.commit()
        
        return work.work_id
    
    async def add_chunk(
        self,
        work_id: str,
        sequence: int,
        chunk_type: str,
        content: str,
        modern_translation: str = "",
        is_key_sentence: bool = False,
        difficulty: int = 3,
        tags: Dict = None
    ) -> str:
        """지문 분할 추가"""
        
        chunk = TextChunk(
            chunk_id=str(uuid.uuid4()),
            work_id=work_id,
            sequence=sequence,
            chunk_type=chunk_type,
            content=content,
            modern_translation=modern_translation,
            is_key_sentence=is_key_sentence,
            difficulty=difficulty,
            tags=tags or {}
        )
        
        self.db.add(chunk)
        await self.db.commit()
        
        return chunk.chunk_id
    
    async def index_rag_document(
        self,
        doc_type: str,
        content: str,
        work_id: Optional[str] = None,
        chunk_id: Optional[str] = None,
        usage_stages: List[str] = None,
        priority: int = 5
    ) -> str:
        """RAG 문서 인덱싱"""
        
        doc = RAGDocument(
            doc_id=str(uuid.uuid4()),
            doc_type=doc_type,
            work_id=work_id,
            chunk_id=chunk_id,
            content=content,
            usage_stages=usage_stages or [],
            priority=priority
        )
        
        self.db.add(doc)
        await self.db.commit()
        
        return doc.doc_id
    
    async def get_rag_documents_for_stage(
        self,
        stage_id: str,
        work_id: Optional[str] = None,
        chunk_id: Optional[str] = None
    ) -> List[Dict]:
        """특정 단계에 사용할 RAG 문서 조회"""
        
        stmt = select(RAGDocument).where(
            RAGDocument.usage_stages.contains([stage_id])
        )
        
        if work_id:
            stmt = stmt.where(RAGDocument.work_id == work_id)
        if chunk_id:
            stmt = stmt.where(RAGDocument.chunk_id == chunk_id)
        
        stmt = stmt.order_by(RAGDocument.priority.desc())
        
        result = await self.db.execute(stmt)
        docs = result.scalars().all()
        
        return [
            {
                "doc_id": doc.doc_id,
                "doc_type": doc.doc_type,
                "content": doc.content,
                "priority": doc.priority
            }
            for doc in docs
        ]
