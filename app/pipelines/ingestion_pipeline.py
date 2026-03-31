import uuid
from pathlib import Path

from app.pipelines.chunking import split_text
from app.services.embedding_service import EmbeddingService
from app.repositories.vector_repository import VectorRepository
from app.core.config import settings


class IngestionPipeline:
    """
    문서 파일 → Vector DB 저장까지의 전체 파이프라인.
    순서: 파싱 → 정제 → 청킹 → 임베딩 → 저장
    """

    def __init__(
        self,
        embedding_service: EmbeddingService,
        vector_repository: VectorRepository,
    ):
        self.embedding_service = embedding_service
        self.vector_repository = vector_repository

    async def run(self, file_path: str, filename: str) -> int:
        """
        파이프라인 실행.
        Returns:
            저장된 청크 수
        """
        # 1. 문서 파싱 — (텍스트, 페이지번호) 쌍 목록 반환
        pages = self._parse(file_path)  # [(text, page_no), ...]

        # 2. 텍스트 정제 + 청킹 (페이지별로 처리 후 합산)
        all_chunks: list[str] = []
        all_page_nos: list[int] = []

        for page_text, page_no in pages:
            cleaned = self._clean(page_text)
            page_chunks = split_text(
                text=cleaned,
                chunk_size=settings.rag_chunk_size,
                chunk_overlap=settings.rag_chunk_overlap,
            )
            all_chunks.extend(page_chunks)
            all_page_nos.extend([page_no] * len(page_chunks))

        chunks = all_chunks
        if not chunks:
            return 0

        # 3. 배치 임베딩 (32개씩 나눠서 처리)
        all_embeddings = []
        batch_size = 32
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            embeddings = await self.embedding_service.embed_batch(batch)
            all_embeddings.extend(embeddings)

        # 4. 메타데이터 구성 및 Vector DB 저장
        # ChromaDB 제약: 메타데이터 값은 str/int/float/bool 만 허용 (None 불가)
        metadatas = [
            {"source": filename, "chunk_index": i, "page": all_page_nos[i]}
            for i in range(len(chunks))
        ]
        ids = [f"{filename}_{i}_{uuid.uuid4().hex[:8]}" for i in range(len(chunks))]

        self.vector_repository.add_chunks(
            chunks=chunks,
            embeddings=all_embeddings,
            metadatas=metadatas,
            ids=ids,
        )

        return len(chunks)

    def _parse(self, file_path: str) -> list[tuple[str, int]]:
        """
        파일에서 텍스트 추출.
        반환: [(텍스트, 페이지번호), ...]
          - txt/md: 전체를 1개 페이지(0)로 취급
          - pdf: 페이지별로 분리
        """
        path = Path(file_path)
        suffix = path.suffix.lower()

        if suffix in [".txt", ".md"]:
            text = path.read_text(encoding="utf-8")
            return [(text, 0)]  # 페이지 개념 없음 → 0으로 통일
        elif suffix == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(file_path)
                return [
                    (page.extract_text() or "", page_no + 1)
                    for page_no, page in enumerate(reader.pages)
                ]
            except ImportError:
                raise ValueError("PDF 처리를 위해 pypdf를 설치하세요: pip install pypdf")
        else:
            raise ValueError(f"지원하지 않는 파일 형식: {suffix}")

    def _clean(self, text: str) -> str:
        """기본 텍스트 정제"""
        import re
        # 연속된 빈 줄 제거
        text = re.sub(r"\n{3,}", "\n\n", text)
        # 앞뒤 공백 제거
        text = text.strip()
        return text
