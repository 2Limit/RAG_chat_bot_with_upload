from app.core.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.llm_service import LLMService
from app.repositories.vector_repository import VectorRepository
from app.schemas.chat import SourceDocument

# 시스템 프롬프트: LLM에게 역할과 규칙을 부여
SYSTEM_PROMPT = """당신은 문서 기반 QA 어시스턴트입니다.

규칙:
1. 반드시 아래 [참고 문서]에 있는 내용만을 근거로 답변하세요.
2. 참고 문서에 관련 내용이 없으면 "제공된 문서에서 해당 내용을 찾을 수 없습니다."라고 답하세요.
3. 답변은 명확하고 간결하게 작성하세요.
4. 출처를 임의로 만들어내지 마세요.
"""


class RAGService:
    """
    RAG 핵심 파이프라인 오케스트레이터.
    검색(Retrieval) + 생성(Generation)을 조율한다.
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_repository: VectorRepository,
        llm_service: LLMService,
    ):
        self.embedding_service = embedding_service
        self.vector_repository = vector_repository
        self.llm_service = llm_service

    async def answer(
        self,
        question: str,
        chat_history: list[dict],
    ) -> tuple[str, list[SourceDocument]]:
        """
        질문에 대한 RAG 기반 답변 생성.

        Returns:
            (answer_text, source_documents)
        """
        # 1. 질문 임베딩
        query_embedding = await self.embedding_service.embed_text(question)

        # 2. Vector DB 유사 문서 검색
        chunks = self.vector_repository.search(
            query_embedding=query_embedding,
            top_k=settings.rag_top_k,
            score_threshold=settings.rag_score_threshold,
        )

        # 3. 관련 문서가 없으면 즉시 반환
        if not chunks:
            return "제공된 문서에서 해당 내용을 찾을 수 없습니다.", []

        # 4. 컨텍스트 구성
        context_parts = []
        sources = []
        for i, chunk in enumerate(chunks, 1):
            meta = chunk["metadata"]
            context_parts.append(
                f"[문서{i}] 출처: {meta.get('source', '알 수 없음')} "
                f"(p.{meta.get('page', '?')})\n{chunk['text']}"
            )
            sources.append(
                SourceDocument(
                    filename=meta.get("source", "알 수 없음"),
                    page=meta.get("page"),
                    score=round(chunk["score"], 3),
                )
            )

        context = "\n\n".join(context_parts)

        # 5. 프롬프트 구성 (컨텍스트 + 히스토리 + 질문)
        messages = list(chat_history)  # 이전 대화 히스토리
        messages.append({
            "role": "user",
            "content": f"[참고 문서]\n{context}\n\n[질문]\n{question}",
        })

        # 6. LLM 호출
        answer = await self.llm_service.generate(
            system_prompt=SYSTEM_PROMPT,
            messages=messages,
        )

        return answer, sources
