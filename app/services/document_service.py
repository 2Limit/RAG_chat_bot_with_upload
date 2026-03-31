import uuid
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.document import Document
from app.pipelines.ingestion_pipeline import IngestionPipeline
from app.schemas.document import DocumentUploadResponse, DocumentListItem, DocumentDeleteResponse


class DocumentService:
    """문서 업로드 처리 및 목록 조회"""

    def __init__(self, ingestion_pipeline: IngestionPipeline):
        self.pipeline = ingestion_pipeline

    async def upload(
        self,
        filename: str,
        content: bytes,
        db: AsyncSession,
    ) -> DocumentUploadResponse:
        # 1. 파일 저장
        save_path = Path("data/raw") / filename
        save_path.write_bytes(content)

        # 2. DB에 문서 메타데이터 저장 (status: processing)
        doc = Document(
            filename=filename,
            file_path=str(save_path),
            status="processing",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        # 3. 인제스천 파이프라인 실행 (청킹 → 임베딩 → 벡터 저장)
        chunk_count = await self.pipeline.run(
            file_path=str(save_path),
            filename=filename,
        )

        # 4. 완료 상태 업데이트
        doc.chunk_count = chunk_count
        doc.status = "completed"
        await db.commit()

        return DocumentUploadResponse(
            document_id=doc.id,
            filename=filename,
            chunk_count=chunk_count,
            status="completed",
            message=f"{chunk_count}개 청크가 Vector DB에 저장되었습니다.",
        )

    async def list_documents(self, db: AsyncSession) -> list[DocumentListItem]:
        result = await db.execute(
            select(Document).order_by(Document.created_at.desc())
        )
        docs = result.scalars().all()
        return [DocumentListItem.model_validate(doc) for doc in docs]

    async def delete(self, document_id: int, db: AsyncSession) -> DocumentDeleteResponse:
        # 1. RDB에서 문서 조회
        result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        doc = result.scalar_one_or_none()
        if doc is None:
            raise HTTPException(status_code=404, detail="문서를 찾을 수 없습니다.")

        filename = doc.filename
        deleted_chunks = doc.chunk_count

        # 2. Vector DB에서 해당 파일의 청크 전체 삭제
        self.pipeline.vector_repository.delete_by_source(filename)

        # 3. 파일 시스템에서 원본 파일 삭제
        file_path = Path(doc.file_path)
        if file_path.exists():
            file_path.unlink()

        # 4. RDB에서 문서 행 삭제
        await db.delete(doc)
        await db.commit()

        return DocumentDeleteResponse(
            message="문서가 삭제되었습니다.",
            filename=filename,
            deleted_chunks=deleted_chunks,
        )
