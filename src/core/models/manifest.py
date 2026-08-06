from datetime import datetime
from typing import final

from pydantic import Field

from core.common.schema import CamelCaseModel
from core.models.book import BookStatus
from core.models.chapter import Chapter


@final
class TTSSnapshot(CamelCaseModel):
    """Soniox settings captured in the manifest (no secrets)."""

    model: str = Field(..., description="Soniox TTS model id")
    voice: str = Field(..., description="Provider voice id")
    language: str = Field(..., description="Narration language code")
    speed: float = Field(..., description="Speech rate multiplier")
    audio_format: str = Field(..., description="Requested audio container")


@final
class MergeSnapshot(CamelCaseModel):
    """Audio merge settings captured in the manifest."""

    bitrate: str = Field(..., description="Output MP3 bitrate")
    sample_rate: int = Field(..., description="Output sample rate, Hz")


@final
class ProcessingSettings(CamelCaseModel):
    """Snapshot of the settings used for a run (secrets excluded)."""

    tts: TTSSnapshot
    merge: MergeSnapshot


@final
class BookManifest(CamelCaseModel):
    """Per-book manifest tracking overall status and detected chapters."""

    source_file: str = Field(
        ..., description="Original input file name, e.g. book.pdf"
    )
    slug: str = Field(..., description="Book slug used as the output folder")
    status: BookStatus = Field(
        default=BookStatus.PENDING, description="Overall pipeline status"
    )
    started_at: datetime | None = Field(
        default=None, description="UTC timestamp of the first run"
    )
    settings: ProcessingSettings | None = Field(
        default=None, description="Settings snapshot used for this run"
    )
    chapters: list[Chapter] = Field(
        default_factory=list, description="Chapters detected so far"
    )
