from enum import StrEnum
from typing import final


@final
class BookStatus(StrEnum):
    """Book processing status, advancing as pipeline stages complete."""

    PENDING = "pending"
    TEXT_EXTRACTED = "text_extracted"
    CHAPTERS_READY = "chapters_ready"
    TRANSLATED = "translated"
    AUDIO_GENERATED = "audio_generated"
    COMPLETED = "completed"
