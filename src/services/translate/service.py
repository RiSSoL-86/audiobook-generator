import asyncio
import re
from typing import TYPE_CHECKING, final, override

from core.common.service import BaseService
from services.translate.clients.openai import OpenAITranslateClient

if TYPE_CHECKING:
    from core.models.chapter import Chapter
    from core.paths import BookPaths
    from services.translate.clients.base import TranslateClient


@final
class TranslateService(BaseService):
    """Translates a chapter's markdown in paragraph-aligned batches."""

    PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
    PARAGRAPH_JOIN = "\n\n"
    MAX_BACKOFF_SECONDS = 30

    def __init__(self) -> None:
        super().__init__()
        self.translate_client: TranslateClient = OpenAITranslateClient()

    @override
    async def execute(
        self,
        chapters: list[Chapter],
        paths: BookPaths,
        force: bool = False,
    ) -> None:
        """Translate each chapter's markdown, skipping already-done files."""
        semaphore = asyncio.Semaphore(self.settings.translate.concurrency)

        async def worker(chapter: Chapter) -> None:
            output = paths.chapter_translated_file(chapter.index)
            if output.exists() and not force:
                return
            source = paths.chapter_file(chapter.index).read_text(
                encoding="utf-8"
            )
            async with semaphore:
                translated = await self._translate_text(text=source)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(translated, encoding="utf-8")
            self.logger.info(msg=f"Translated chapter {chapter.index}")

        await asyncio.gather(*(worker(chapter) for chapter in chapters))

    async def _translate_text(self, text: str) -> str:
        """Return the translated markdown, batched to bound request size."""
        batches = self._batches(text=text)
        translated = [await self._translate(batch=batch) for batch in batches]
        return self.PARAGRAPH_JOIN.join(translated)

    def _batches(self, text: str) -> list[str]:
        """Pack whole paragraphs up to the char cap, never splitting one."""
        cap = self.settings.translate.batch_max_chars
        batches: list[str] = []
        current = ""
        for raw in self.PARAGRAPH_SPLIT.split(text):
            paragraph = raw.strip()
            if not paragraph:
                continue
            if not current:
                current = paragraph
                continue
            candidate = f"{current}{self.PARAGRAPH_JOIN}{paragraph}"
            if len(candidate) <= cap:
                current = candidate
            else:
                batches.append(current)
                current = paragraph
        if current:
            batches.append(current)
        return batches

    async def _translate(self, batch: str) -> str:
        """Translate one batch, retrying transient failures with backoff."""
        last_error = "unknown error"
        for attempt in range(self.settings.translate.max_retries + 1):
            try:
                result = await self.translate_client.translate(
                    text=batch,
                    source_lang=self.settings.translate.source_lang,
                    target_lang=self.settings.translate.target_lang,
                )
            except Exception as exc:
                last_error = str(exc)
                self.logger.warning(
                    msg=f"Translation attempt {attempt + 1} failed"
                )
                if attempt < self.settings.translate.max_retries:
                    backoff = min(2**attempt, self.MAX_BACKOFF_SECONDS)
                    await asyncio.sleep(backoff)
                continue
            return result.text
        msg = f"Translation failed after retries: {last_error}"
        raise RuntimeError(msg)
