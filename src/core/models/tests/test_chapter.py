import pytest
from pydantic import ValidationError

from core.models.chapter import Chapter
from core.models.chunk import Chunk, ChunkStatus


def make_chunk(index: int, status: ChunkStatus = ChunkStatus.PENDING) -> Chunk:
    return Chunk(index=index, chapter_index=1, char_count=10, status=status)


def make_chapter(chunks: list[Chunk] | None = None) -> Chapter:
    return Chapter(
        index=1, raw_title="Intro", slug="intro", chunks=chunks or []
    )


def test_chunk_total_counts_chunks() -> None:
    assert make_chapter([make_chunk(1), make_chunk(2)]).chunk_total == 2
    assert make_chapter().chunk_total == 0


def test_audio_complete_is_false_without_chunks() -> None:
    assert make_chapter().audio_complete is False


def test_audio_complete_is_true_when_all_generated() -> None:
    chunks = [make_chunk(i, ChunkStatus.GENERATED) for i in (1, 2)]
    assert make_chapter(chunks).audio_complete is True


def test_audio_complete_is_false_when_any_pending() -> None:
    chunks = [
        make_chunk(1, ChunkStatus.GENERATED),
        make_chunk(2, ChunkStatus.PENDING),
    ]
    assert make_chapter(chunks).audio_complete is False


def test_index_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        Chapter(index=0, raw_title="x", slug="x")


def test_duration_seconds_must_be_non_negative() -> None:
    with pytest.raises(ValidationError):
        Chapter(index=1, raw_title="x", slug="x", duration_seconds=-1.0)
