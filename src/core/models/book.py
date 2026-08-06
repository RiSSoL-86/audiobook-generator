from enum import StrEnum
from typing import final


@final
class BookStatus(StrEnum):
    """Book processing status, advancing as pipeline stages complete."""

    PENDING = "pending"
    TEXT_EXTRACTED = "text_extracted"
    CHAPTERS_READY = "chapters_ready"
    AUDIO_GENERATED = "audio_generated"
    COMPLETED = "completed"
