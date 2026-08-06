from enum import StrEnum
from typing import final

from pydantic import Field

from core.common.schema import CamelCaseModel


@final
class ChunkStatus(StrEnum):
    """Per-chunk TTS generation status."""

    PENDING = "pending"
    GENERATED = "generated"
    FAILED = "failed"


@final
class Chunk(CamelCaseModel):
    """A chapter text block sent to the TTS provider as one request."""

    index: int = Field(
        ..., ge=1, description="1-based block order within its chapter"
    )
    chapter_index: int = Field(
        ..., ge=1, description="Index of the owning chapter"
    )
    char_count: int = Field(
        ..., ge=0, description="Number of characters in the block"
    )
    status: ChunkStatus = Field(
        default=ChunkStatus.PENDING, description="TTS generation status"
    )
    error: str | None = Field(
        default=None, description="Last TTS error message, if any"
    )
    request_id: str | None = Field(
        default=None, description="Provider request id of the last attempt"
    )
