from pathlib import Path

from pydantic_settings import SettingsConfigDict

SRC_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = SRC_DIR.parent
ENV_FILE = SRC_DIR / ".env"


def env_config(prefix: str = "") -> SettingsConfigDict:
    """Shared settings config; ``prefix`` namespaces env vars per domain."""
    return SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_prefix=prefix,
        extra="ignore",
    )
