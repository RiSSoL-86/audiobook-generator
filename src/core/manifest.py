import time
from typing import TYPE_CHECKING

from core.models.manifest import BookManifest

if TYPE_CHECKING:
    from pathlib import Path


class ManifestRepository:
    """Loads and atomically persists a single book's manifest.json."""

    REPLACE_RETRIES = 5
    REPLACE_BACKOFF = 0.1

    def __init__(self, path: Path) -> None:
        self.path = path

    def exists(self) -> bool:
        """Return whether the manifest file is present on disk."""
        return self.path.exists()

    def load(self) -> BookManifest:
        """Read and validate the manifest from disk."""
        return BookManifest.model_validate_json(
            self.path.read_text(encoding="utf-8")
        )

    def save(self, manifest: BookManifest) -> None:
        """Write the manifest atomically via a temp file and replace."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(f"{self.path.name}.tmp")
        tmp.write_text(
            manifest.model_dump_json(indent=2, by_alias=True),
            encoding="utf-8",
        )
        for attempt in range(self.REPLACE_RETRIES):
            try:
                tmp.replace(self.path)
            except PermissionError:
                if attempt == self.REPLACE_RETRIES - 1:
                    raise
                time.sleep(self.REPLACE_BACKOFF)
            else:
                return
