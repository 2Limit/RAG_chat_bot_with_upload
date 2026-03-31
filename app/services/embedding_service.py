from sentence_transformers import SentenceTransformer

from app.core.config import settings


class EmbeddingService:
    """
    sentence-transformers를 사용해 텍스트를 벡터로 변환 (로컬 실행).
    - 외부 API 불필요, 무료, 무제한
    - 첫 실행 시 모델 자동 다운로드 (~120MB)
    - 기본 모델: intfloat/multilingual-e5-small (한국어 포함 다국어 지원)
    """

    def __init__(self):
        model_name = settings.huggingface_embedding_model
        print(f"[EmbeddingService] 모델 로딩 중: {model_name} (device: cpu)")
        self._model = SentenceTransformer(model_name, device="cpu")
        print(f"[EmbeddingService] 모델 로딩 완료")

    async def embed_text(self, text: str) -> list[float]:
        """텍스트 1개를 임베딩 벡터로 변환"""
        embeddings = await self.embed_batch([text])
        return embeddings[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """텍스트 목록을 배치로 임베딩"""
        # sentence-transformers는 동기 라이브러리이므로 직접 호출
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return vectors.tolist()
