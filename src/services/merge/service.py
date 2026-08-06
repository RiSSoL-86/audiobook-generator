import asyncio
from typing import TYPE_CHECKING, final, override

import aiofiles
import aiofiles.os

from core.common.service import BaseService
from services.merge.schemas import MergeResult

if TYPE_CHECKING:
    from pathlib import Path

    from core.models.chapter import Chapter
    from core.paths import BookPaths


@final
class MergeService(BaseService):
    """Concatenates a chapter's audio chunks into one MP3 via ffmpeg."""

    ERROR_TAIL = 500

    @override
    async def execute(self, chapter: Chapter, paths: BookPaths) -> MergeResult:
        """Merge all chunks of a chapter into its final MP3 file."""
        audio_files = [
            paths.chunk_audio_file(chapter.index, chunk.index)
            for chunk in chapter.chunks
        ]
        exists = await asyncio.gather(
            *(aiofiles.os.path.exists(path) for path in audio_files)
        )
        missing = [
            path
            for path, ok in zip(audio_files, exists, strict=True)
            if not ok
        ]
        if not audio_files or missing:
            detail = ", ".join(path.name for path in missing) or "no chunks"
            msg = f"chapter {chapter.index} has missing audio chunks: {detail}"
            raise RuntimeError(msg)
        output = paths.chapter_mp3_file(chapter.index, chapter.slug)
        await aiofiles.os.makedirs(output.parent, exist_ok=True)
        await self._concat(files=audio_files, output=output)
        return MergeResult(
            mp3_file=output.name,
            duration_seconds=await self._probe_duration(path=output),
        )

    async def _concat(self, files: list[Path], output: Path) -> None:
        """Concatenate and re-encode files for consistent, seekable output."""
        list_path = output.with_suffix(".txt")
        entries = "\n".join(
            f"file '{path.resolve().as_posix()}'" for path in files
        )
        async with aiofiles.open(
            list_path, "w", encoding="utf-8"
        ) as list_file:
            await list_file.write(entries + "\n")
        try:
            await self._run(
                self.settings.app.ffmpeg_path,
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-ar",
                str(self.settings.merge.sample_rate),
                "-b:a",
                self.settings.merge.bitrate,
                str(output),
            )
        finally:
            if await aiofiles.os.path.exists(list_path):
                await aiofiles.os.remove(list_path)

    async def _probe_duration(self, path: Path) -> float | None:
        """Return the media duration in seconds via ffprobe, if available."""
        proc = await asyncio.create_subprocess_exec(
            self.settings.app.ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await proc.communicate()
        if proc.returncode != 0:
            return None
        try:
            return float(stdout.decode().strip())
        except ValueError:
            return None

    async def _run(self, *cmd: str) -> None:
        """Run a subprocess and raise with stderr tail on non-zero exit."""
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await proc.communicate()
        if proc.returncode != 0:
            detail = stderr.decode(errors="replace").strip()[
                -self.ERROR_TAIL :
            ]
            msg = f"ffmpeg failed ({proc.returncode}): {detail}"
            raise RuntimeError(msg)
