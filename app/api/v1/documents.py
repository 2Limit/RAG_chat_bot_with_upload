from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_embedding_service, get_vector_repository
from app.services.document_service import DocumentService
from app.pipelines.ingestion_pipeline import IngestionPipeline
from app.schemas.document import DocumentUploadResponse, DocumentListItem, DocumentDeleteResponse

from app.core.auth import current_owner
from app.core.config import settings
from app.services.document_service import safe_filename

router = APIRouter()

ALLOWED_EXTENSIONS = {".txt", ".md", ".pdf"}


def get_document_service(
    embedding_service=Depends(get_embedding_service),
    vector_repository=Depends(get_vector_repository),
) -> DocumentService:
    pipeline = IngestionPipeline(embedding_service, vector_repository)
    return DocumentService(pipeline)


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    owner_id: str = Depends(current_owner),
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
):
    """
    문서 파일 업로드 및 Vector DB 저장.
    지원 형식: .txt, .md, .pdf
    """
    safe_filename(file.filename or "")
    content = bytearray()
    try:
        while chunk := await file.read(64 * 1024):
            content.extend(chunk)
            if len(content) > settings.max_upload_bytes:
                raise HTTPException(413, "Document exceeds upload limit")
    finally:
        await file.close()
    return await doc_service.upload(
        filename=file.filename,
        content=bytes(content),
        owner_id=owner_id,
        db=db,
    )


@router.get("/documents", response_model=list[DocumentListItem])
async def list_documents(
    owner_id: str = Depends(current_owner),
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
):
    """업로드된 문서 목록 조회"""
    return await doc_service.list_documents(db, owner_id)


@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: int,
    owner_id: str = Depends(current_owner),
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
):
    """
    문서 삭제 — RDB 행 + Vector DB 청크 + 원본 파일 모두 제거.
    """
    return await doc_service.delete(document_id, db, owner_id)
