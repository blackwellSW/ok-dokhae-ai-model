
from pydantic import BaseModel
from typing import Optional, Dict, List
from datetime import datetime

class LiteraryWorkBase(BaseModel):
    work_id: str
    title: str
    author: str
    period: str
    difficulty: int
    genre: str
    description: Optional[str] = None
    keywords: Dict = {}

class LiteraryWorkCreate(LiteraryWorkBase):
    pass

class LiteraryWork(LiteraryWorkBase):
    created_at: str
    updated_at: str

class TextChunkBase(BaseModel):
    chunk_id: str
    work_id: str
    sequence: int
    chunk_type: str
    content: str
    modern_translation: Optional[str] = None
    is_key_sentence: bool = False
    difficulty: int = 3
    tags: Dict = {}

class TextChunkCreate(TextChunkBase):
    pass

class TextChunk(TextChunkBase):
    created_at: str
