from pathlib import Path
from typing import final

from pydantic import Field
from pydantic_settings import BaseSettings

from app_settings.base import PROJECT_ROOT, env_config


@final
class AppSettings(BaseSettings):
    """Cross-cutting settings: I/O locations and logging."""

    model_config = env_config("APP_")

    input_dir: Path = Field(
        default_factory=lambda: PROJECT_ROOT / "input",
        description="Folder scanned for source files",
    )
    output_dir: Path = Field(
        default_factory=lambda: PROJECT_ROOT / "output",
        description="Folder for per-book result trees",
    )
    ffmpeg_path: str = Field(
        default="ffmpeg", description="ffmpeg name or absolute path"
    )
    ffprobe_path: str = Field(
        default="ffprobe", description="ffprobe name or absolute path"
    )
    log_level: str = Field(default="INFO", description="Root log level")
