from typing import final

from pydantic import Field
from pydantic_settings import BaseSettings

from app_settings.base import env_config


@final
class MergeSettings(BaseSettings):
    """Per-chapter MP3 merge settings (ffmpeg)."""

    model_config = env_config("MERGE_")

    bitrate: str = Field(default="128k", description="Output MP3 bitrate")
    sample_rate: int = Field(
        default=44100, gt=0, description="Output sample rate, Hz"
    )
