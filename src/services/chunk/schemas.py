from typing import final

from core.models.chunk import Chunk
from services.common.schema import Schema


@final
class ChunkContent(Schema):
    """A text block paired with its chunk metadata."""

    chunk: Chunk
    text: str
