"""
기본 단위 테스트 예시.
실행: pytest tests/ -v
"""
import pytest
from app.pipelines.chunking import split_text


def test_split_text_basic():
    text = "첫 번째 문단입니다.\n\n두 번째 문단입니다.\n\n세 번째 문단입니다."
    chunks = split_text(text, chunk_size=30, chunk_overlap=5)
    assert len(chunks) > 0
    assert all(isinstance(c, str) for c in chunks)


def test_split_text_empty():
    assert split_text("") == []


def test_split_text_single_para():
    text = "짧은 문단"
    chunks = split_text(text, chunk_size=500)
    assert chunks == ["짧은 문단"]


def test_split_text_overlap():
    long_text = "A" * 200
    chunks = split_text(long_text, chunk_size=100, chunk_overlap=20)
    # overlap이 있으므로 청크 수 > 2
    assert len(chunks) >= 2
