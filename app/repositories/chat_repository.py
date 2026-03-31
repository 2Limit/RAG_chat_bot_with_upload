from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.chat import ChatSession, ChatMessage


class ChatRepository:
    """채팅 세션 & 메시지 CRUD"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_session(self, session_id: str) -> ChatSession:
        result = await self.db.execute(
            select(ChatSession).where(ChatSession.session_id == session_id)
        )
        session = result.scalar_one_or_none()

        if session is None:
            session = ChatSession(session_id=session_id)
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)

        return session

    async def get_recent_messages(
        self, session_id: str, limit: int = 6
    ) -> list[ChatMessage]:
        """최근 N개 메시지 조회 (히스토리 컨텍스트용)"""
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )
        messages = result.scalars().all()
        return list(reversed(messages))  # 시간순 정렬

    async def save_message(self, session_id: str, role: str, content: str) -> ChatMessage:
        message = ChatMessage(session_id=session_id, role=role, content=content)
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        return message
