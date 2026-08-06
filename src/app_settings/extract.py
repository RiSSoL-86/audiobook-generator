from typing import final

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings

from app_settings.base import env_config


@final
class ExtractSettings(BaseSettings):
    """PDF text extraction settings."""

    model_config = env_config("EXTRACT_")

    llama_cloud_api_key: SecretStr | None = Field(
        default=None, description="LlamaParse API key"
    )
