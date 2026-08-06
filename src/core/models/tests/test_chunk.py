import pytest
from pydantic import ValidationError

from core.models.chunk import Chunk, ChunkStatus


def test_defaults() -> None:
    chunk = Chunk(index=1, chapter_index=1, char_count=5)
    assert chunk.status is ChunkStatus.PENDING
    assert chunk.error is None
    assert chunk.request_id is None


def test_accepts_camel_case_aliases() -> None:
    chunk = Chunk.model_validate(
        {"index": 2, "chapterIndex": 3, "charCount": 8, "requestId": "req-1"}
    )
    assert chunk.chapter_index == 3
    assert chunk.char_count == 8
    assert chunk.request_id == "req-1"


def test_serializes_camel_case_aliases() -> None:
    chunk = Chunk(index=1, chapter_index=1, char_count=5)
    dumped = chunk.model_dump(by_alias=True)
    assert "chapterIndex" in dumped
    assert "charCount" in dumped
    assert "requestId" in dumped


@pytest.mark.parametrize(
    ("index", "chapter_index", "char_count"),
    [(0, 1, 5), (1, 0, 5), (1, 1, -1)],
)
def test_rejects_out_of_range_values(
    index: int, chapter_index: int, char_count: int
) -> None:
    with pytest.raises(ValidationError):
        Chunk(index=index, chapter_index=chapter_index, char_count=char_count)


def test_chunk_status_values() -> None:
    assert ChunkStatus.PENDING.value == "pending"
    assert ChunkStatus.GENERATED.value == "generated"
    assert ChunkStatus.FAILED.value == "failed"
