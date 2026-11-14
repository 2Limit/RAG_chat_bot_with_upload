import logging
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from app.core.revisions import OwnerRevision, ensure_revision
from app.models.chat import ChatSession, ChatMessage

from app.core.config import settings
from app.models.document import Document
from app.schemas.document import DocumentUploadResponse, DocumentListItem, DocumentDeleteResponse

logger = logging.getLogger(__name__)


def safe_filename(filename: str) -> str:
    # Reject rather than silently normalize paths. Display names are never storage keys.
    if (not filename or len(filename) > 255 or filename in {".", ".."}
            or any(c in filename for c in '/\\:')
            or any(ord(c) < 32 or ord(c) == 127 for c in filename)):
        raise HTTPException(400, "Invalid filename")
    if Path(filename).suffix.lower() not in {".txt", ".md", ".pdf"}:
        raise HTTPException(400, "Only txt, md and pdf are supported")
    return filename


class DocumentService:
    def __init__(self, ingestion_pipeline):
        self.pipeline = ingestion_pipeline

    def _path(self, doc):
        root = Path(settings.raw_path).resolve()
        root.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = root / f"{doc.id}{Path(doc.filename).suffix.lower()}"
        # Storage is service-private. Refuse unexpected symlinks rather than follow them.
        if path.is_symlink():
            raise RuntimeError("Unsafe storage path")
        return path

    async def upload(self, filename: str, content: bytes, db: AsyncSession, owner_id: str):
        filename = safe_filename(filename)
        if not content or len(content) > settings.max_upload_bytes:
            raise HTTPException(413 if content else 400, "Empty or oversized document")
        doc = Document(owner_id=owner_id, filename=filename, file_path="", status="processing")
        db.add(doc)
        await db.commit()
        await db.refresh(doc)
        doc_id = doc.id
        created_file = False
        ingestion_started = False
        try:
            path = self._path(doc)
            with path.open("xb") as stream:
                created_file = True
                stream.write(content)
            doc.file_path = str(path)
            await db.commit()
            ingestion_started = True
            count = await self.pipeline.run(str(path), filename, owner_id, doc_id)
            if not count:
                raise ValueError("No extractable text in document")
            doc.chunk_count = count
            doc.status = "completed"
            await db.commit()
        except Exception:
            await db.rollback()
            # Persist failed before cleanup. Search only sees completed IDs, so even
            # cleanup failure cannot re-expose partial ingestion. DELETE can retry.
            doc = await db.get(Document, doc_id)
            doc.status = "failed"
            # Empty path means this attempt never owned a file; DELETE must not
            # remove an unrelated pre-existing path after an exclusive-open error.
            doc.file_path = str(path) if created_file else ""
            await db.commit()
            try:
                if ingestion_started:
                    self.pipeline.vector_repository.delete_document(owner_id, doc_id)
                if created_file:
                    self._path(doc).unlink(missing_ok=True)
            except Exception:
                logger.exception("Document cleanup requires retry: %s", doc_id)
            raise HTTPException(422, "Document processing failed; delete the failed entry and retry")
        return DocumentUploadResponse(document_id=doc.id, filename=filename,
            chunk_count=count, status="completed", message=f"{count} chunks stored")

    async def list_documents(self, db: AsyncSession, owner_id: str):
        docs = (await db.scalars(select(Document).where(Document.owner_id == owner_id)
                               .order_by(Document.created_at.desc()))).all()
        return [DocumentListItem.model_validate(doc) for doc in docs]

    async def delete(self, document_id: int, db: AsyncSession, owner_id: str):
        await ensure_revision(db, owner_id)
        doc = await db.scalar(select(Document).where(Document.id == document_id,
                                                    Document.owner_id == owner_id))
        if doc is None:
            raise HTTPException(404, "Document not found")
        filename, count = doc.filename, doc.chunk_count
        # Durable tombstone excludes chunks from new retrievals before removing them.
        await db.execute(update(OwnerRevision).where(OwnerRevision.owner_id == owner_id)
                         .values(revision=OwnerRevision.revision + 1))
        doc.status = "deleting"
        # Past answers may contain the deleted document. Clear this owner's
        # histories rather than accidentally reuse those excerpts in future chats.
        sessions = select(ChatSession.session_id).where(ChatSession.owner_id == owner_id)
        await db.execute(delete(ChatMessage).where(ChatMessage.session_id.in_(sessions)))
        await db.commit()
        try:
            self.pipeline.vector_repository.delete_document(owner_id, doc.id)
            if doc.file_path:
                self._path(doc).unlink(missing_ok=True)
            await db.delete(doc)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Document deletion requires retry: %s", document_id)
            raise HTTPException(503, "Deletion incomplete; your conversation history has already been cleared and in-flight answers invalidated. Retry this document ID.")
        return DocumentDeleteResponse(message="Document deleted", filename=filename, deleted_chunks=count)
