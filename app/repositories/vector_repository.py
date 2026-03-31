import chromadb
from chromadb.config import Settings as ChromaSettings

from app.core.config import settings


class VectorRepository:
    """
    ChromaDB와의 모든 통신을 담당.
    Service 레이어는 이 클래스만 사용하고 ChromaDB를 직접 다루지 않는다.
    """

    def __init__(self):
        self._client = chromadb.PersistentClient(
            path=settings.vectordb_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=settings.vectordb_collection,
            metadata={"hnsw:space": "cosine"},  # cosine 유사도 사용
        )

    def add_chunks(
        self,
        chunks: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict],
        ids: list[str],
    ) -> None:
        """청크 텍스트 + 임베딩 + 메타데이터를 Vector DB에 저장"""
        self._collection.upsert(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadatas,
            ids=ids,
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        score_threshold: float = 0.7,
    ) -> list[dict]:
        """
        쿼리 임베딩과 가장 유사한 청크를 검색.
        반환: [{ text, metadata, score }, ...]
        """
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # ChromaDB cosine distance → similarity 변환 (distance가 낮을수록 유사)
            score = 1 - dist
            if score >= score_threshold:
                chunks.append({"text": doc, "metadata": meta, "score": score})

        return chunks

    def delete_by_source(self, filename: str) -> None:
        """특정 파일의 모든 청크 삭제 (문서 재업로드 시 사용)"""
        self._collection.delete(where={"source": filename})

    def count(self) -> int:
        return self._collection.count()
