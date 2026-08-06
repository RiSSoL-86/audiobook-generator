from typing import final

from services.common.schema import Schema


@final
class MergeResult(Schema):
    """Outcome of merging one chapter's audio chunks into a single MP3."""

    mp3_file: str
    duration_seconds: float | None = None
