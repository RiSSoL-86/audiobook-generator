from typing import Self, final

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings

from app_settings.base import env_config


@final
class ChunkSettings(BaseSettings):
    """Text chunking size targets, in characters."""

    model_config = env_config("CHUNK_")

    target_min_chars: int = Field(
        default=600, gt=0, description="Preferred lower bound per chunk"
    )
    target_max_chars: int = Field(
        default=900, gt=0, description="Preferred upper bound per chunk"
    )
    hard_max_chars: int = Field(
        default=1000, gt=0, description="Absolute cap for any chunk"
    )

    @model_validator(mode="after")
    def _check_order(self) -> Self:
        """Ensure target_min <= target_max <= hard_max."""
        ordered = (
            self.target_min_chars
            <= self.target_max_chars
            <= self.hard_max_chars
        )
        if not ordered:
            msg = "chunk sizes must be ordered: min <= max <= hard_max"
            raise ValueError(msg)
        return self
