"""
문서 업로드 API
역할: 학습 문서(PDF/TXT/DOCX) 업로드, 텍스트 추출, 청크 분할

📋 프론트엔드 개발자를 위한 사용 가이드
==========================================

1. 문서 업로드: POST /documents
   - multipart/form-data로 파일 전송
   - 응답으로 document_id 받음
   - ✨ Google Document AI로 고품질 OCR 처리

2. 상태 확인: GET /documents/{document_id}
   - status가 "ready"가 될 때까지 폴링

3. 프리뷰 확인: GET /documents/{document_id}/preview
   - 업로드 확인 모달에 표시할 텍스트

4. 청크 조회: GET /documents/{document_id}/chunks
   - 세션 시작 시 chunk_id 선택용
"""

from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
import os
import tempfile

# from sqlalchemy.ext.asyncio import AsyncSession  # Removed
# from sqlalchemy import select  # Removed
# from app.db.session import get_db  # Removed
# from app.db.models import User, RAGDocument, TextChunk  # Removed

from app.schemas.user import User
from app.schemas.document import RAGDocumentCreate
from app.schemas.work import TextChunkCreate
from app.repository.document_repository import DocumentRepository
from app.repository.work_repository import WorkRepository
from app.core.auth import get_current_user
from app.services.document_ai import get_document_ai_service

# Helper function
def split_into_chunks(text: str, chunk_size: int = 500) -> List[Dict]:
    """텍스트를 청크로 분할"""
    chunks = []
    
    # 문단 단위로 먼저 분리
    paragraphs = text.split("\n\n")
    
    current_chunk = ""
    current_start = 0
    sequence = 1
    
    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append({
                "sequence": sequence,
                "text": current_chunk.strip(),
                "anchor": {
                    "char_start": current_start,
                    "char_end": current_start + len(current_chunk),
                    "paragraph": sequence
                }
            })
            sequence += 1
            current_start += len(current_chunk)
            current_chunk = para + "\n\n"
        else:
            current_chunk += para + "\n\n"
    
    # 마지막 청크
    if current_chunk.strip():
        chunks.append({
            "sequence": sequence,
            "text": current_chunk.strip(),
            "anchor": {
                "char_start": current_start,
                "char_end": current_start + len(current_chunk),
                "paragraph": sequence
            }
        })
    
    return chunks

router = APIRouter(prefix="/documents", tags=["📄 Document Management"])


# ============================================================
# Request/Response Models - 프론트엔드 개발자 참고용 상세 설명
# ============================================================

class DocumentUploadResponse(BaseModel):
    """
    문서 업로드 응답
    """
    document_id: str = Field(..., description="문서 고유 ID. 이후 모든 API 호출에 사용", example="doc_abc123")
    status: str = Field(..., description="처리 상태: processing(처리중) | ready(완료) | failed(실패)", example="processing")
    message: str = Field(..., description="사용자에게 표시할 메시지", example="문서가 업로드되었습니다.")
    meta: Dict[str, Any] = Field(default_factory=dict, description="파일 메타데이터")


class DocumentStatusResponse(BaseModel):
    """
    문서 상태 조회 응답
    """
    document_id: str = Field(..., description="문서 고유 ID")
    status: str = Field(..., description="처리 상태", example="ready")
    title: Optional[str] = Field(None, description="문서 제목")
    total_chunks: int = Field(0, description="분할된 청크 수")
    total_chars: int = Field(0, description="총 문자 수")
    created_at: str = Field(..., description="생성 시각 (ISO 8601)")
    error_message: Optional[str] = Field(None, description="실패 시 에러 메시지")


class DocumentPreviewResponse(BaseModel):
    """
    문서 프리뷰 응답 - 업로드 확인 모달용
    """
    document_id: str
    title: Optional[str]
    preview: Dict[str, str] = Field(..., description="앞/중간/뒷부분 미리보기")
    total_chars: int


class ChunkItem(BaseModel):
    """
    청크 정보 - 세션 시작 시 chunk_id 선택에 사용
    """
    chunk_id: str = Field(..., description="청크 고유 ID", example="chunk_001")
    sequence: int = Field(..., description="순서 (1부터 시작)", example=1)
    text: str = Field(..., description="청크 텍스트 내용")
    anchor: Dict[str, Any] = Field(..., description="위치 정보 {page, paragraph, char_start, char_end}")


class DocumentChunksResponse(BaseModel):
    """
    문서 청크 목록 응답
    """
    document_id: str
    chunks: List[ChunkItem]
    total_chunks: int


# ============================================================
# API Endpoints
# ============================================================

@router.post(
    "",
    response_model=DocumentUploadResponse,
    summary="📤 문서 업로드",
    description="문서를 업로드하고 처리합니다."
)
async def upload_document(
    file: UploadFile = File(..., description="업로드할 문서 파일 (PDF/TXT/DOCX)"),
    title: Optional[str] = Form(None, description="문서 제목 (생략 시 파일명 사용)"),
    current_user: User = Depends(get_current_user)
):
    """
    문서 업로드 및 텍스트 추출
    """
    
    # 파일 크기 체크 (10MB)
    MAX_SIZE = 10 * 1024 * 1024
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="파일 크기가 10MB를 초과합니다"
        )
    
    # 임시 파일 저장 (Cloud Run에서는 /tmp 사용)
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"{uuid.uuid4()}_{file.filename}")
    
    try:
        with open(temp_path, "wb") as f:
            f.write(content)
        
        # Document AI 서비스를 통한 텍스트 추출
        doc_service = get_document_ai_service()
        result = await doc_service.process_document(
            file_path=temp_path,
            mime_type=file.content_type or "application/pdf"
        )
        extracted_text = result["text"]
        
        # 청크 분할
        chunks = split_into_chunks(extracted_text)
        
        # 문서 ID 생성
        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        doc_title = title or os.path.splitext(file.filename)[0]
        
        # RAGDocument 저장 (Firestore)
        doc_repo = DocumentRepository()
        doc_create = RAGDocumentCreate(
            doc_id=doc_id,
            doc_type="uploaded",
            content=extracted_text,
            usage_stages=["LEARNING"],
            priority=5
        )
        await doc_repo.create_document(doc_create)
        
        # TextChunk 저장 (Firestore)
        work_repo = WorkRepository()
        for chunk_data in chunks:
            chunk_create = TextChunkCreate(
                chunk_id=f"{doc_id}_chunk_{chunk_data['sequence']:03d}",
                work_id=doc_id,  # 문서 ID를 work_id로 사용
                sequence=chunk_data["sequence"],
                chunk_type="paragraph",
                content=chunk_data["text"],
                tags=chunk_data["anchor"]
            )
            await work_repo.create_chunk(chunk_create)
        
        return DocumentUploadResponse(
            document_id=doc_id,
            status="ready",
            message="문서가 성공적으로 처리되었습니다.",
            meta={
                "filename": file.filename,
                "file_size": len(content),
                "mime_type": file.content_type,
                "total_chars": len(extracted_text),
                "total_chunks": len(chunks),
                "source": result.get("source", "unknown")
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"문서 처리 실패: {str(e)}"
        )
    finally:
        # 임시 파일 삭제
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get(
    "/{document_id}",
    response_model=DocumentStatusResponse,
    summary="📋 문서 상태 조회"
)
async def get_document_status(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """문서 상태 조회"""
    
    doc_repo = DocumentRepository()
    doc = await doc_repo.get_document(document_id)
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"문서를 찾을 수 없습니다: {document_id}"
        )
    
    # 청크 수 조회 (Firestore)
    work_repo = WorkRepository()
    chunks = await work_repo.get_chunks_by_work(document_id)
    
    return DocumentStatusResponse(
        document_id=document_id,
        status="ready",
        title=document_id,  # 실제로는 별도 title 필드 필요하지만 스키마에 없음
        total_chunks=len(chunks),
        total_chars=len(doc.content) if doc.content else 0,
        created_at=doc.created_at
    )


@router.get(
    "/{document_id}/preview",
    response_model=DocumentPreviewResponse,
    summary="👁️ 문서 프리뷰 조회"
)
async def get_document_preview(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """문서 프리뷰 조회"""
    
    doc_repo = DocumentRepository()
    doc = await doc_repo.get_document(document_id)
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"문서를 찾을 수 없습니다: {document_id}"
        )
    
    content = doc.content or ""
    total_len = len(content)
    
    # 앞/중간/뒤 각 200자
    preview_len = 200
    
    preview = {
        "beginning": content[:preview_len] + ("..." if total_len > preview_len else ""),
        "middle": "",
        "end": ""
    }
    
    if total_len > preview_len * 2:
        mid_start = (total_len - preview_len) // 2
        preview["middle"] = "..." + content[mid_start:mid_start + preview_len] + "..."
    
    if total_len > preview_len:
        preview["end"] = "..." + content[-preview_len:]
    
    return DocumentPreviewResponse(
        document_id=document_id,
        title=document_id,
        preview=preview,
        total_chars=total_len
    )


@router.get(
    "/{document_id}/chunks",
    response_model=DocumentChunksResponse,
    summary="📑 문서 청크 목록 조회"
)
async def get_document_chunks(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """문서 청크 목록 조회"""
    
    work_repo = WorkRepository()
    chunks = await work_repo.get_chunks_by_work(document_id)
    
    if not chunks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"문서 청크를 찾을 수 없습니다: {document_id}"
        )
    
    chunk_items = [
        ChunkItem(
            chunk_id=chunk.chunk_id,
            sequence=chunk.sequence,
            text=chunk.content,
            anchor=chunk.tags if chunk.tags else {"paragraph": chunk.sequence}
        )
        for chunk in chunks
    ]
    
    return DocumentChunksResponse(
        document_id=document_id,
        chunks=chunk_items,
        total_chunks=len(chunk_items)
    )


@router.get(
    "",
    summary="📚 내 문서 목록 조회"
)
async def list_documents(
    current_user: User = Depends(get_current_user)
):
    """내 문서 목록 조회"""
    
    doc_repo = DocumentRepository()
    # 현재는 모든 문서 반환
    docs = await doc_repo.get_documents_by_type("uploaded")
    
    return {
        "documents": [
            {
                "document_id": doc.doc_id,
                "title": doc.doc_id,
                "status": "ready",
                "total_chars": len(doc.content) if doc.content else 0,
                "created_at": doc.created_at
            }
            for doc in docs
        ],
        "total": len(docs)
    }
