from typing import final

from pydantic import Field

from core.common.schema import CamelCaseModel
from core.models.chunk import Chunk, ChunkStatus


@final
class Chapter(CamelCaseModel):
    """Metadata of one chapter; body lives in text/chapter_NNN.md."""

    index: int = Field(
        ..., ge=1, description="1-based chapter order in the book"
    )
    raw_title: str = Field(
        ..., description="Original heading text as found in the book"
    )
    slug: str = Field(
        ..., description="Filesystem-safe title used in output file names"
    )
    page_start: int | None = Field(
        default=None, description="First source PDF page, if known"
    )
    page_end: int | None = Field(
        default=None, description="Last source PDF page, if known"
    )
    chunks: list[Chunk] = Field(
        default_factory=list, description="Text blocks, in reading order"
    )
    mp3_file: str | None = Field(
        default=None, description="Final chapter MP3 file name, once merged"
    )
    duration_seconds: float | None = Field(
        default=None, ge=0, description="Final MP3 duration, if measured"
    )

    @property
    def chunk_total(self) -> int:
        """Number of text blocks in this chapter."""
        return len(self.chunks)

    @property
    def audio_complete(self) -> bool:
        """Whether every chunk of this chapter has been voiced."""
        return bool(self.chunks) and all(
            chunk.status is ChunkStatus.GENERATED for chunk in self.chunks
        )
