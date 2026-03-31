from pydantic import BaseModel, Field
from datetime import datetime


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000, description="사용자 질문")
    session_id: str = Field(..., min_length=1, max_length=64, description="대화 세션 ID")


class SourceDocument(BaseModel):
    """응답에 사용된 출처 문서 정보"""
    filename: str
    page: int | None = None
    score: float


class ChatResponse(BaseModel):
    answer: str
    session_id: str
    sources: list[SourceDocument] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ChatHistoryItem(BaseModel):
    role: str   # "user" | "assistant"
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}
