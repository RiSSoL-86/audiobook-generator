from typing import final

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from app_settings.base import env_config


@final
class TranslateSettings(BaseSettings):
    """OpenAI chapter translation settings."""

    model_config = env_config("TRANSLATE_")

    openai_api_key: SecretStr | None = Field(
        default=None, description="OpenAI API key for the translate stage"
    )
    model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model id used for translation",
    )
    source_lang: str = Field(
        default="en", description="Source language code of the source book"
    )
    target_lang: str = Field(
        default="ru", description="Target language code for the translation"
    )
    batch_max_chars: int = Field(
        default=6000,
        ge=1,
        description="Max characters per translation request; long "
        "chapters are split on paragraph boundaries into batches",
    )
    max_retries: int = Field(
        default=3, ge=0, description="Retries per batch on failure"
    )
    request_timeout: float = Field(
        default=300.0, gt=0, description="Per-request timeout, seconds"
    )
    concurrency: int = Field(
        default=3, ge=1, description="Parallel translation requests"
    )
