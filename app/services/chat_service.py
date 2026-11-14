import hashlib
import json
from sqlalchemy import select, update
from fastapi import HTTPException
from app.core.revisions import OwnerRevision, ensure_revision, read_revision
from app.models.chat import ChatMessage
from app.models.document import Document
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.chat_repository import ChatRepository
from app.services.rag_service import RAGService
from app.schemas.chat import ChatRequest, ChatResponse


class ChatService:
    """
    채팅 요청 처리 오케스트레이터.
    히스토리 조회 → RAG 실행 → 결과 저장의 흐름을 관리한다.
    """

    def __init__(self, rag_service: RAGService):
        self.rag_service = rag_service

    async def chat(self, request: ChatRequest, db: AsyncSession, owner_id: str) -> ChatResponse:
        session_key = hashlib.sha256(json.dumps([owner_id, request.session_id]).encode()).hexdigest()
        repo = ChatRepository(db)

        # 1. 세션 확보 (없으면 생성)
        await repo.get_or_create_session(session_key, owner_id)

        await ensure_revision(db, owner_id)
        revision = await read_revision(db, owner_id)

        # 2. 최근 대화 히스토리 조회 (최근 3턴 = 6개 메시지)
        recent_messages = await repo.get_recent_messages(
            session_key, limit=6
        )
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in recent_messages
        ]

        ids = list((await db.scalars(select(Document.id).where(
            Document.owner_id == owner_id, Document.status == "completed"))).all())

        # Do not hold a SQLite read snapshot during an external model call.
        await db.commit()

        # 3. RAG 파이프라인 실행
        answer, sources = await self.rag_service.answer(
            question=request.message,
            chat_history=chat_history,
            owner_id=owner_id, document_ids=ids,
        )

        # Conditional write acquires the same DB write lock as deletion. Checking
        # and saving in one transaction prevents a stale answer from repopulating
        # history after deletion, even across processes sharing this SQLite DB.
        result = await db.execute(update(OwnerRevision).where(
            OwnerRevision.owner_id == owner_id, OwnerRevision.revision == revision
        ).values(revision=revision))
        if result.rowcount != 1:
            await db.rollback()
            raise HTTPException(409, "Documents/history changed while answering; response discarded. Ask again.")
        db.add_all([
            ChatMessage(session_id=session_key, role="user", content=request.message),
            ChatMessage(session_id=session_key, role="assistant", content=answer),
        ])
        await db.commit()

        return ChatResponse(
            answer=answer,
            session_id=request.session_id,
            sources=sources,
        )
