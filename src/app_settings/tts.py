from typing import final

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from app_settings.base import env_config


@final
class TTSSettings(BaseSettings):
    """Soniox TTS narration settings."""

    model_config = env_config("TTS_")

    soniox_api_key: SecretStr | None = Field(
        default=None, description="Soniox API key for the TTS stage"
    )
    model: str = Field(
        default="", description="Soniox TTS model id (to confirm)"
    )
    voice: str = Field(
        default="", description="Provider voice id (to confirm)"
    )
    language: str = Field(default="ru", description="Narration language code")
    speed: float = Field(
        default=1.0, gt=0, description="Speech rate multiplier"
    )
    audio_format: str = Field(
        default="mp3", description="Requested audio container"
    )
    max_retries: int = Field(
        default=3, ge=0, description="Retries per chunk on failure"
    )
    request_timeout: float = Field(
        default=60.0, gt=0, description="Per-request timeout, seconds"
    )
    concurrency: int = Field(
        default=3,
        ge=1,
        description="Parallel TTS requests (Soniox allows 3 streams)",
    )
