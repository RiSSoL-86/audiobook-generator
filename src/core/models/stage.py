from enum import IntEnum, StrEnum
from typing import final


@final
class Stage(IntEnum):
    """Pipeline stages, ordered for resume filtering."""

    EXTRACT = 1
    CHAPTERS = 2
    CHUNK = 3
    TTS = 4
    MERGE = 5

    @property
    def banner(self) -> str:
        """Stage header for logs, e.g. ``Stage 1/5: Extract text``."""
        titles = {
            Stage.EXTRACT: "Extract text",
            Stage.CHAPTERS: "Detect chapters",
            Stage.CHUNK: "Split into chunks",
            Stage.TTS: "Generate audio",
            Stage.MERGE: "Merge MP3 files",
        }
        return f"Stage {self.value}/{len(Stage)}: {titles[self]}"


@final
class FromStage(StrEnum):
    """CLI values selecting the first stage to run."""

    EXTRACT = "extract"
    CHAPTERS = "chapters"
    CHUNK = "chunk"
    TTS = "tts"
    MERGE = "merge"

    @property
    def stage(self) -> Stage:
        """Map the CLI value to its ordered stage."""
        return Stage[self.name]
