from typing import TYPE_CHECKING

import pytest

from core.models.chapter import Chapter
from core.paths import BookPaths
from core.utils import slugify

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from core.models.chunk import Chunk


@pytest.fixture
def book_paths(tmp_path: Path) -> BookPaths:
    """A BookPaths rooted in an isolated temp directory."""
    return BookPaths(root=tmp_path / "book")


@pytest.fixture
def make_chapter() -> Callable[..., Chapter]:
    """Factory for Chapter models with sensible defaults."""

    def build(
        index: int = 1,
        raw_title: str = "Chapter",
        chunks: list[Chunk] | None = None,
    ) -> Chapter:
        return Chapter(
            index=index,
            raw_title=raw_title,
            slug=slugify(raw_title),
            chunks=chunks or [],
        )

    return build
