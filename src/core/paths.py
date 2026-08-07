from pathlib import Path
from typing import final

from pydantic import BaseModel, ConfigDict

from core.utils import chapter_dir_name, padded_index


@final
class BookPaths(BaseModel):
    """Resolves every output path for a single book under its root."""

    model_config = ConfigDict(frozen=True)

    root: Path

    @property
    def manifest_file(self) -> Path:
        """Path to the book's ``manifest.json``."""
        return self.root / "manifest.json"

    @property
    def text_dir(self) -> Path:
        """Directory holding the cleaned text and per-chapter markdown."""
        return self.root / "text"

    @property
    def chunks_dir(self) -> Path:
        """Directory holding per-chapter text chunk folders."""
        return self.root / "chunks"

    @property
    def audio_chunks_dir(self) -> Path:
        """Directory holding per-chapter audio chunk folders."""
        return self.root / "audio_chunks"

    @property
    def mp3_dir(self) -> Path:
        """Directory holding the final one-file-per-chapter MP3s."""
        return self.root / "mp3"

    @property
    def full_text_file(self) -> Path:
        """Path to the cleaned full-book markdown."""
        return self.text_dir / "full_text.md"

    def chapter_file(self, index: int) -> Path:
        """Path to a chapter's markdown, e.g. ``text/chapter_001.md``."""
        return self.text_dir / f"{chapter_dir_name(index)}.md"

    def chapter_chunks_dir(self, chapter_index: int) -> Path:
        """Directory holding a chapter's text chunks."""
        return self.chunks_dir / chapter_dir_name(chapter_index)

    def chunk_file(self, chapter_index: int, chunk_index: int) -> Path:
        """Path to a single text chunk, e.g. ``chunk_001.txt``."""
        name = f"chunk_{padded_index(chunk_index)}.txt"
        return self.chapter_chunks_dir(chapter_index) / name

    def chapter_audio_dir(self, chapter_index: int) -> Path:
        """Directory holding a chapter's audio chunks."""
        return self.audio_chunks_dir / chapter_dir_name(chapter_index)

    def chunk_audio_file(self, chapter_index: int, chunk_index: int) -> Path:
        """Path to a single audio chunk, e.g. ``chunk_001.mp3``."""
        name = f"chunk_{padded_index(chunk_index)}.mp3"
        return self.chapter_audio_dir(chapter_index) / name

    def chapter_mp3_file(self, index: int, slug: str) -> Path:
        """Path to a final chapter MP3, e.g. ``mp3/001_intro.mp3``."""
        name = f"{padded_index(index)}_{slug}.mp3"
        return self.mp3_dir / name
