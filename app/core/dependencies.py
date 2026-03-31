"""
의존성 주입(DI) 모음.
Router에서 Depends()로 서비스 객체를 주입받을 때 이 파일을 사용한다.
"""
from functools import lru_cache

from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService
from app.services.chat_service import ChatService
from app.repositories.vector_repository import VectorRepository


@lru_cache
def get_embedding_service() -> EmbeddingService:
    """임베딩 서비스 (앱 전체에서 1개 인스턴스 재사용)"""
    return EmbeddingService()


@lru_cache
def get_vector_repository() -> VectorRepository:
    """Vector DB 저장소 (앱 전체에서 1개 인스턴스 재사용)"""
    return VectorRepository()


@lru_cache
def get_llm_service() -> LLMService:
    """LLM 서비스 (앱 전체에서 1개 인스턴스 재사용)"""
    return LLMService()


def get_rag_service() -> RAGService:
    return RAGService(
        embedding_service=get_embedding_service(),
        vector_repository=get_vector_repository(),
        llm_service=get_llm_service(),
    )


def get_chat_service() -> ChatService:
    return ChatService(rag_service=get_rag_service())
