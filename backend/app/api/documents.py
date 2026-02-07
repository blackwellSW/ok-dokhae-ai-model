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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid
import os
import tempfile

from app.db.session import get_db
from app.db.models import User, RAGDocument, TextChunk
from app.core.auth import get_current_user
from app.services.document_ai import get_document_ai_service

router = APIRouter(prefix="/documents", tags=["📄 Document Management"])


# ============================================================
# Request/Response Models - 프론트엔드 개발자 참고용 상세 설명
# ============================================================

class DocumentUploadResponse(BaseModel):
    """
    문서 업로드 응답
    
    Example:
    ```json
    {
        "document_id": "doc_abc123",
        "status": "processing",
        "message": "문서가 업로드되었습니다. 처리 중입니다.",
        "meta": {
            "filename": "춘향전.pdf",
            "file_size": 102400,
            "mime_type": "application/pdf"
        }
    }
    ```
    """
    document_id: str = Field(..., description="문서 고유 ID. 이후 모든 API 호출에 사용", example="doc_abc123")
    status: str = Field(..., description="처리 상태: processing(처리중) | ready(완료) | failed(실패)", example="processing")
    message: str = Field(..., description="사용자에게 표시할 메시지", example="문서가 업로드되었습니다.")
    meta: Dict[str, Any] = Field(default_factory=dict, description="파일 메타데이터")


class DocumentStatusResponse(BaseModel):
    """
    문서 상태 조회 응답
    
    - status가 "ready"가 되면 preview/chunks 조회 가능
    - "failed"인 경우 error_message 확인
    
    Example:
    ```json
    {
        "document_id": "doc_abc123",
        "status": "ready",
        "title": "춘향전",
        "total_chunks": 15,
        "total_chars": 12500,
        "created_at": "2026-02-06T12:00:00Z"
    }
    ```
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
    
    - 앞/중간/뒷부분 미리보기 제공
    - 사용자가 올바른 문서인지 확인하는 용도
    
    Example:
    ```json
    {
        "document_id": "doc_abc123",
        "title": "춘향전",
        "preview": {
            "beginning": "남원 고을에 이도령이라 하는 양반이...",
            "middle": "춘향이 그네를 타는 모습을 보고...",
            "end": "이도령과 춘향은 백년해로하였다."
        },
        "total_chars": 12500
    }
    ```
    """
    document_id: str
    title: Optional[str]
    preview: Dict[str, str] = Field(..., description="앞/중간/뒷부분 미리보기")
    total_chars: int


class ChunkItem(BaseModel):
    """
    청크 정보 - 세션 시작 시 chunk_id 선택에 사용
    
    anchor: 문서 내 위치 정보 (근거 표시용)
    """
    chunk_id: str = Field(..., description="청크 고유 ID", example="chunk_001")
    sequence: int = Field(..., description="순서 (1부터 시작)", example=1)
    text: str = Field(..., description="청크 텍스트 내용")
    anchor: Dict[str, Any] = Field(..., description="위치 정보 {page, paragraph, char_start, char_end}")


class DocumentChunksResponse(BaseModel):
    """
    문서 청크 목록 응답
    
    - 세션 시작 시 work_id/chunk_id 선택에 사용
    - 각 청크에 anchor 정보 포함 (근거 위치 표시용)
    
    Example:
    ```json
    {
        "document_id": "doc_abc123",
        "chunks": [
            {
                "chunk_id": "chunk_001",
                "sequence": 1,
                "text": "남원 고을에 이도령이라 하는 양반이...",
                "anchor": {"page": 1, "paragraph": 1, "char_start": 0, "char_end": 150}
            }
        ],
        "total_chunks": 15
    }
    ```
    """
    document_id: str
    chunks: List[ChunkItem]
    total_chunks: int


# ============================================================
# 헬퍼 함수
# ============================================================




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


# ============================================================
# API Endpoints
# ============================================================

@router.post(
    "",
    response_model=DocumentUploadResponse,
    summary="📤 문서 업로드",
    description="""
    학습용 문서를 업로드합니다.
    
    ## 지원 형식
    - **PDF**: .pdf
    - **텍스트**: .txt
    - **Word**: .docx
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const formData = new FormData();
    formData.append('file', fileInput.files[0]);
    formData.append('title', '춘향전');
    
    const response = await fetch('/documents', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
        body: formData
    });
    const data = await response.json();
    console.log(data.document_id); // 이 ID로 이후 API 호출
    ```
    
    ## 주의사항
    - 최대 파일 크기: 10MB
    - 업로드 후 처리에 수 초 소요될 수 있음
    - status가 "ready"가 될 때까지 폴링 필요
    """
)
async def upload_document(
    file: UploadFile = File(..., description="업로드할 문서 파일 (PDF/TXT/DOCX)"),
    title: Optional[str] = Form(None, description="문서 제목 (생략 시 파일명 사용)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    문서 업로드 및 텍스트 추출
    
    1. 파일을 임시 저장
    2. 텍스트 추출
    3. 청크로 분할
    4. DB에 저장
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
        # (서비스 내부에서 pypdf fallback 처리 포함)
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
        
        # RAGDocument 저장
        doc = RAGDocument(
            doc_id=doc_id,
            doc_type="uploaded",
            content=extracted_text,
            usage_stages=["LEARNING"],
            priority=5
        )
        db.add(doc)
        
        # TextChunk 저장
        for chunk_data in chunks:
            chunk = TextChunk(
                chunk_id=f"{doc_id}_chunk_{chunk_data['sequence']:03d}",
                work_id=doc_id,  # 문서 ID를 work_id로 사용
                sequence=chunk_data["sequence"],
                chunk_type="paragraph",
                content=chunk_data["text"],
                tags=chunk_data["anchor"]
            )
            db.add(chunk)
        
        await db.commit()
        
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
    summary="📋 문서 상태 조회",
    description="""
    업로드된 문서의 처리 상태를 조회합니다.
    
    ## 상태 값
    - `processing`: 처리 중 (폴링 계속)
    - `ready`: 완료 (preview/chunks 조회 가능)
    - `failed`: 실패 (error_message 확인)
    
    ## 사용 예시 (JavaScript)
    ```javascript
    // 폴링 예시
    const checkStatus = async (docId) => {
        const res = await fetch(`/documents/${docId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const data = await res.json();
        
        if (data.status === 'ready') {
            // 프리뷰 표시
            showPreview(docId);
        } else if (data.status === 'processing') {
            // 2초 후 재시도
            setTimeout(() => checkStatus(docId), 2000);
        } else {
            // 에러 처리
            showError(data.error_message);
        }
    };
    ```
    """
)
async def get_document_status(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """문서 상태 조회"""
    
    # 문서 조회
    stmt = select(RAGDocument).where(RAGDocument.doc_id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"문서를 찾을 수 없습니다: {document_id}"
        )
    
    # 청크 수 조회
    chunk_stmt = select(TextChunk).where(TextChunk.work_id == document_id)
    chunk_result = await db.execute(chunk_stmt)
    chunks = chunk_result.scalars().all()
    
    return DocumentStatusResponse(
        document_id=document_id,
        status="ready",
        title=document_id,  # 실제로는 별도 title 필드 필요
        total_chunks=len(chunks),
        total_chars=len(doc.content) if doc.content else 0,
        created_at=doc.created_at.isoformat() if doc.created_at else datetime.now().isoformat()
    )


@router.get(
    "/{document_id}/preview",
    response_model=DocumentPreviewResponse,
    summary="👁️ 문서 프리뷰 조회",
    description="""
    문서의 앞/중간/뒷부분 미리보기를 제공합니다.
    
    ## 용도
    - 업로드 확인 모달에서 사용자가 올바른 문서인지 확인
    - 각 부분 최대 200자
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch(`/documents/${docId}/preview`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const { preview } = await res.json();
    
    document.getElementById('previewBegin').innerText = preview.beginning;
    document.getElementById('previewMiddle').innerText = preview.middle;
    document.getElementById('previewEnd').innerText = preview.end;
    ```
    """
)
async def get_document_preview(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """문서 프리뷰 조회"""
    
    stmt = select(RAGDocument).where(RAGDocument.doc_id == document_id)
    result = await db.execute(stmt)
    doc = result.scalar_one_or_none()
    
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
    summary="📑 문서 청크 목록 조회",
    description="""
    문서가 분할된 청크 목록을 조회합니다.
    
    ## 용도
    - 세션 시작 시 학습할 chunk_id 선택
    - 근거 표시를 위한 anchor 정보 포함
    
    ## anchor 구조
    ```json
    {
        "char_start": 0,      // 시작 문자 위치
        "char_end": 150,      // 끝 문자 위치
        "paragraph": 1        // 문단 번호
    }
    ```
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch(`/documents/${docId}/chunks`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const { chunks } = await res.json();
    
    // 청크 선택 UI 렌더링
    chunks.forEach(chunk => {
        addChunkOption(chunk.chunk_id, chunk.text.slice(0, 50) + '...');
    });
    ```
    """
)
async def get_document_chunks(
    document_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """문서 청크 목록 조회"""
    
    stmt = select(TextChunk).where(TextChunk.work_id == document_id).order_by(TextChunk.sequence)
    result = await db.execute(stmt)
    chunks = result.scalars().all()
    
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
    summary="📚 내 문서 목록 조회",
    description="""
    현재 사용자가 업로드한 문서 목록을 조회합니다.
    
    ## 사용 예시 (JavaScript)
    ```javascript
    const res = await fetch('/documents', {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    const { documents } = await res.json();
    
    documents.forEach(doc => {
        console.log(doc.document_id, doc.title);
    });
    ```
    """
)
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """내 문서 목록 조회"""
    
    # 현재는 모든 문서 반환 (추후 user_id 필터 추가)
    stmt = select(RAGDocument).where(RAGDocument.doc_type == "uploaded")
    result = await db.execute(stmt)
    docs = result.scalars().all()
    
    return {
        "documents": [
            {
                "document_id": doc.doc_id,
                "title": doc.doc_id,
                "status": "ready",
                "total_chars": len(doc.content) if doc.content else 0,
                "created_at": doc.created_at.isoformat() if doc.created_at else None
            }
            for doc in docs
        ],
        "total": len(docs)
    }
