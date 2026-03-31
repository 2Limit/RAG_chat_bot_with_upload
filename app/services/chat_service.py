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

    async def chat(self, request: ChatRequest, db: AsyncSession) -> ChatResponse:
        repo = ChatRepository(db)

        # 1. 세션 확보 (없으면 생성)
        await repo.get_or_create_session(request.session_id)

        # 2. 최근 대화 히스토리 조회 (최근 3턴 = 6개 메시지)
        recent_messages = await repo.get_recent_messages(
            request.session_id, limit=6
        )
        chat_history = [
            {"role": msg.role, "content": msg.content}
            for msg in recent_messages
        ]

        # 3. RAG 파이프라인 실행
        answer, sources = await self.rag_service.answer(
            question=request.message,
            chat_history=chat_history,
        )

        # 4. 대화 저장
        await repo.save_message(request.session_id, "user", request.message)
        await repo.save_message(request.session_id, "assistant", answer)

        return ChatResponse(
            answer=answer,
            session_id=request.session_id,
            sources=sources,
        )
