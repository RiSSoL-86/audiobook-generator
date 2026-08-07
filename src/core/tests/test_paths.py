from pathlib import Path

import pytest
from pydantic import ValidationError

from core.paths import BookPaths


def make_paths() -> BookPaths:
    return BookPaths(root=Path("/out/my_book"))


def test_model_is_frozen() -> None:
    paths = make_paths()
    with pytest.raises(ValidationError):
        paths.root = Path("/elsewhere")


def test_top_level_paths() -> None:
    paths = make_paths()
    assert paths.manifest_file == paths.root / "manifest.json"
    assert paths.text_dir == paths.root / "text"
    assert paths.chunks_dir == paths.root / "chunks"
    assert paths.audio_chunks_dir == paths.root / "audio_chunks"
    assert paths.mp3_dir == paths.root / "mp3"
    assert paths.full_text_file == paths.root / "text" / "full_text.md"


def test_chapter_file_uses_padded_index() -> None:
    paths = make_paths()
    assert paths.chapter_file(7) == paths.text_dir / "chapter_007.md"


def test_chapter_chunks_dir_and_chunk_file() -> None:
    paths = make_paths()
    assert paths.chapter_chunks_dir(2) == paths.chunks_dir / "chapter_002"
    assert (
        paths.chunk_file(2, 5)
        == paths.chunks_dir / "chapter_002" / "chunk_005.txt"
    )


def test_chapter_audio_dir_and_chunk_audio_file() -> None:
    paths = make_paths()
    assert paths.chapter_audio_dir(2) == paths.audio_chunks_dir / "chapter_002"
    assert (
        paths.chunk_audio_file(2, 5)
        == paths.audio_chunks_dir / "chapter_002" / "chunk_005.mp3"
    )


def test_chapter_mp3_file_includes_padded_index_and_slug() -> None:
    paths = make_paths()
    assert (
        paths.chapter_mp3_file(1, "intro") == paths.mp3_dir / "001_intro.mp3"
    )
