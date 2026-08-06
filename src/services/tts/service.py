import asyncio
from typing import TYPE_CHECKING, final, override

import aiofiles
import aiofiles.os

from core.common.service import BaseService
from core.models.chunk import ChunkStatus
from services.tts.clients.soniox import SonioxTTSClient

if TYPE_CHECKING:
    from collections.abc import Callable

    from core.models.chapter import Chapter
    from core.models.chunk import Chunk
    from core.paths import BookPaths
    from services.tts.clients.base import TTSClient


@final
class TTSService(BaseService):
    """Voices a chapter's chunks, skipping done files and retrying failures."""

    MAX_BACKOFF_SECONDS = 30
    tts_client: TTSClient = SonioxTTSClient()

    @override
    async def execute(
        self,
        chapter: Chapter,
        paths: BookPaths,
        on_progress: Callable[[], None] | None = None,
    ) -> None:
        """Generate any missing audio chunks for one chapter, in order."""
        semaphore = asyncio.Semaphore(self.settings.tts.concurrency)

        async def worker(chunk: Chunk) -> None:
            audio_path = paths.chunk_audio_file(chapter.index, chunk.index)
            already_done = (
                chunk.status is ChunkStatus.GENERATED and audio_path.exists()
            )
            if already_done:
                return
            async with semaphore:
                await self._voice_chunk(
                    chunk=chunk,
                    chapter_index=chapter.index,
                    paths=paths,
                )
            if on_progress is not None:
                on_progress()

        await asyncio.gather(*(worker(chunk) for chunk in chapter.chunks))

    async def _voice_chunk(
        self,
        chunk: Chunk,
        chapter_index: int,
        paths: BookPaths,
    ) -> None:
        text_path = paths.chunk_file(chapter_index, chunk.index)
        audio_path = paths.chunk_audio_file(chapter_index, chunk.index)
        async with aiofiles.open(text_path, encoding="utf-8") as text_file:
            text = await text_file.read()
        last_error = "unknown error"
        for attempt in range(self.settings.tts.max_retries + 1):
            try:
                result = await self.tts_client.synthesize(text=text)
            except Exception as exc:
                last_error = str(exc)
                self.logger.warning(
                    msg=f"Chunk {chapter_index}/{chunk.index} attempt "
                    f"{attempt + 1} failed"
                )
                if attempt < self.settings.tts.max_retries:
                    backoff = min(2**attempt, self.MAX_BACKOFF_SECONDS)
                    await asyncio.sleep(backoff)
                continue
            await aiofiles.os.makedirs(audio_path.parent, exist_ok=True)
            async with aiofiles.open(audio_path, "wb") as audio_file:
                await audio_file.write(result.audio)
            chunk.status = ChunkStatus.GENERATED
            chunk.error = None
            chunk.request_id = result.request_id
            self.logger.info(
                msg=f"Voiced chunk {chapter_index}/{chunk.index} "
                f"-> {audio_path.name}"
            )
            return
        chunk.status = ChunkStatus.FAILED
        chunk.error = last_error
