def split_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 50,
) -> list[str]:
    """
    텍스트를 일정 크기의 청크로 분할.

    전략: 문단 우선 분할 → 크기 초과 시 문자 단위 분할
    chunk_overlap: 청크 간 겹치는 문자 수 (문맥 연속성 유지)
    """
    if not text:
        return []

    # 1단계: 문단 단위로 분할
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks = []
    current_chunk = ""

    for para in paragraphs:
        # 현재 청크에 문단 추가했을 때 크기 확인
        candidate = (current_chunk + "\n\n" + para).strip() if current_chunk else para

        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            # 현재 청크 저장
            if current_chunk:
                chunks.append(current_chunk)

            # 문단 자체가 chunk_size 초과하면 강제 분할
            if len(para) > chunk_size:
                sub_chunks = _split_by_size(para, chunk_size, chunk_overlap)
                chunks.extend(sub_chunks[:-1])
                current_chunk = sub_chunks[-1] if sub_chunks else ""
            else:
                current_chunk = para

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def _split_by_size(text: str, chunk_size: int, overlap: int) -> list[str]:
    """문자 단위 강제 분할 (문단이 너무 긴 경우)"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap  # overlap만큼 뒤로 이동
    return chunks
