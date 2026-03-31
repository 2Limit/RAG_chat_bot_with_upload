from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_embedding_service, get_vector_repository
from app.services.document_service import DocumentService
from app.pipelines.ingestion_pipeline import IngestionPipeline
from app.schemas.document import DocumentUploadResponse, DocumentListItem, DocumentDeleteResponse

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
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
):
    """
    문서 파일 업로드 및 Vector DB 저장.
    지원 형식: .txt, .md, .pdf
    """
    # 확장자 검증
    from pathlib import Path
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식입니다. 허용: {ALLOWED_EXTENSIONS}",
        )

    content = await file.read()
    return await doc_service.upload(
        filename=file.filename,
        content=content,
        db=db,
    )


@router.get("/documents", response_model=list[DocumentListItem])
async def list_documents(
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
):
    """업로드된 문서 목록 조회"""
    return await doc_service.list_documents(db)


@router.delete("/documents/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(
    document_id: int,
    db: AsyncSession = Depends(get_db),
    doc_service: DocumentService = Depends(get_document_service),
):
    """
    문서 삭제 — RDB 행 + Vector DB 청크 + 원본 파일 모두 제거.
    """
    return await doc_service.delete(document_id, db)
