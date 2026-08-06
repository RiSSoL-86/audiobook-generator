from typing import final

from pydantic import BaseModel, Field

from app_settings.app import AppSettings
from app_settings.chunk import ChunkSettings
from app_settings.extract import ExtractSettings
from app_settings.merge import MergeSettings
from app_settings.tts import TTSSettings
from core.models.manifest import (
    MergeSnapshot,
    ProcessingSettings,
    TTSSnapshot,
)


@final
class Settings(BaseModel):
    """All domain settings assembled into one object."""

    app: AppSettings = Field(default_factory=AppSettings)
    extract: ExtractSettings = Field(default_factory=ExtractSettings)
    chunk: ChunkSettings = Field(default_factory=ChunkSettings)
    tts: TTSSettings = Field(default_factory=TTSSettings)
    merge: MergeSettings = Field(default_factory=MergeSettings)

    def to_snapshot(self) -> ProcessingSettings:
        """Capture the non-secret settings recorded in the manifest."""
        return ProcessingSettings(
            tts=TTSSnapshot(
                model=self.tts.model,
                voice=self.tts.voice,
                language=self.tts.language,
                speed=self.tts.speed,
                audio_format=self.tts.audio_format,
            ),
            merge=MergeSnapshot(
                bitrate=self.merge.bitrate,
                sample_rate=self.merge.sample_rate,
            ),
        )


def get_settings() -> Settings:
    """Return the assembled settings object."""
    return Settings()


settings = get_settings()
