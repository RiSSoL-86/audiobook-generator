import asyncio
import shutil
import time
from datetime import UTC, datetime
from pathlib import Path  # noqa: TC003 - runtime type for Typer options
from typing import TYPE_CHECKING, Annotated, final

import typer

from app_settings import settings
from core.chapter_file import read_body, render_chapter
from core.logging import setup_logging
from core.manifest import ManifestRepository
from core.models.book import BookStatus
from core.models.manifest import BookManifest
from core.models.stage import FromStage, Stage
from core.paths import BookPaths
from core.utils import get_logger, slugify
from services.chapter.service import ChapterService
from services.chunk.service import ChunkService
from services.clean.service import CleanService
from services.extract.service import ExtractService
from services.merge.service import MergeService
from services.tts.service import TTSService

if TYPE_CHECKING:
    from core.models.chapter import Chapter

app = typer.Typer(add_completion=False, help="Generate an audiobook from PDF.")


@final
class Pipeline:
    """Runs the ordered stages and persists the manifest between them."""

    PROGRESS_SAVE_INTERVAL = 2.0

    def __init__(
        self,
        pdf_path: Path,
        paths: BookPaths,
        chapter_filter: int | None,
        force: bool,
        dry_run: bool,
    ) -> None:
        self.pdf = pdf_path
        self.paths = paths
        self.chapter = chapter_filter
        self.force = force
        self.dry_run = dry_run
        self.repo = ManifestRepository(path=paths.manifest_file)
        self.manifest = self._load_manifest()
        self.logger = get_logger("pipeline")
        self._last_progress_save = 0.0

    async def run(self, from_stage: Stage, to_stage: Stage) -> None:
        """Execute every stage in the ``[from_stage, to_stage]`` range."""
        if from_stage <= Stage.EXTRACT <= to_stage:
            self.logger.info(msg=Stage.EXTRACT.banner)
            await self._stage_extract()
        if from_stage <= Stage.CHAPTERS <= to_stage:
            self.logger.info(msg=Stage.CHAPTERS.banner)
            await self._stage_chapters()
        if from_stage <= Stage.CHUNK <= to_stage:
            self.logger.info(msg=Stage.CHUNK.banner)
            await self._stage_chunks()
        if from_stage <= Stage.TTS <= to_stage:
            self.logger.info(msg=Stage.TTS.banner)
            await self._stage_tts()
        if from_stage <= Stage.MERGE <= to_stage:
            self.logger.info(msg=Stage.MERGE.banner)
            await self._stage_merge()

    def _load_manifest(self) -> BookManifest:
        if self.repo.exists():
            return self.repo.load()
        return BookManifest(
            source_file=self.pdf.name,
            slug=slugify(value=self.pdf.stem),
            started_at=datetime.now(UTC),
            settings=settings.to_snapshot(),
        )

    def _save(self) -> None:
        if not self.dry_run:
            self.repo.save(manifest=self.manifest)

    def _save_progress(self) -> None:
        now = time.monotonic()
        if now - self._last_progress_save < self.PROGRESS_SAVE_INTERVAL:
            return
        self._last_progress_save = now
        self._save()

    def _chapters(self) -> list[Chapter]:
        if self.chapter is None:
            return self.manifest.chapters
        return [
            chapter
            for chapter in self.manifest.chapters
            if chapter.index == self.chapter
        ]

    async def _stage_extract(self) -> None:
        if not self.force and self.paths.full_text_file.exists():
            self.logger.info(msg="Text already extracted; skipping")
            return
        if self.dry_run:
            return
        self.logger.info(msg=f"Extracting text from {self.pdf.name}")
        extract_service = ExtractService()
        raw = await extract_service.execute(pdf_path=self.pdf)
        clean_service = CleanService()
        clean = await clean_service.execute(raw_text=raw)
        if not clean.strip():
            msg = (
                f"No text extracted from {self.pdf.name}; refusing to cache "
                "an empty result. Check the PDF and extraction settings."
            )
            raise RuntimeError(msg)
        self.paths.text_dir.mkdir(parents=True, exist_ok=True)
        self.paths.full_text_file.write_text(clean, encoding="utf-8")
        self.manifest.status = BookStatus.TEXT_EXTRACTED
        self._save()

    async def _stage_chapters(self) -> None:
        if not self.force and self.manifest.chapters:
            self.logger.info(msg="Chapters already detected; skipping")
            return
        if self.dry_run:
            return
        clean_text = self.paths.full_text_file.read_text(encoding="utf-8")
        chapter_service = ChapterService()
        drafts = await chapter_service.execute(clean_text=clean_text)
        self.paths.text_dir.mkdir(parents=True, exist_ok=True)
        for stale in self.paths.text_dir.glob("chapter_*.md"):
            stale.unlink()
        chapters: list[Chapter] = []
        for draft in drafts:
            file = self.paths.chapter_file(draft.chapter.index)
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text(
                render_chapter(title=draft.chapter.raw_title, body=draft.body),
                encoding="utf-8",
            )
            chapters.append(draft.chapter)
        self.manifest.chapters = chapters
        self.manifest.status = BookStatus.CHAPTERS_READY
        self._save()
        self.logger.info(msg=f"Detected {len(chapters)} chapters")

    async def _stage_chunks(self) -> None:
        chunk_service = ChunkService()
        for chapter in self._chapters():
            if chapter.chunks and not self.force:
                continue
            raw = self.paths.chapter_file(chapter.index).read_text(
                encoding="utf-8"
            )
            contents = await chunk_service.execute(
                body=read_body(text=raw), chapter_index=chapter.index
            )
            self.logger.info(
                msg=f"Chapter {chapter.index} split into "
                f"{len(contents)} chunks"
            )
            if self.dry_run:
                continue
            for stale_dir in (
                self.paths.chapter_chunks_dir(chapter.index),
                self.paths.chapter_audio_dir(chapter.index),
            ):
                if stale_dir.exists():
                    shutil.rmtree(stale_dir)
            chapter.chunks = [content.chunk for content in contents]
            for content in contents:
                file = self.paths.chunk_file(
                    chapter.index, content.chunk.index
                )
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text(content.text, encoding="utf-8")
            self._save()

    async def _stage_tts(self) -> None:
        if self.dry_run:
            return
        tts_service = TTSService()
        for chapter in self._chapters():
            if not chapter.chunks:
                continue
            self.logger.info(
                msg=f"Voicing chapter {chapter.index} "
                f"({chapter.chunk_total} chunks)"
            )
            await tts_service.execute(
                chapter=chapter,
                paths=self.paths,
                on_progress=self._save_progress,
            )
            self._save()
        chapters = self.manifest.chapters
        if chapters and all(chapter.audio_complete for chapter in chapters):
            self.manifest.status = BookStatus.AUDIO_GENERATED
            self._save()

    async def _stage_merge(self) -> None:
        if self.dry_run:
            return
        merge_service = MergeService()
        for chapter in self._chapters():
            if not chapter.audio_complete:
                self.logger.warning(
                    f"Chapter {chapter.index} not fully voiced; skipping merge"
                )
                continue
            existing = (
                chapter.mp3_file is not None
                and (self.paths.mp3_dir / chapter.mp3_file).exists()
            )
            if existing and not self.force:
                continue
            result = await merge_service.execute(
                chapter=chapter, paths=self.paths
            )
            chapter.mp3_file = result.mp3_file
            chapter.duration_seconds = result.duration_seconds
            self._save()
            self.logger.info(
                msg=f"Merged chapter {chapter.index} -> {result.mp3_file}"
            )
        chapters = self.manifest.chapters
        if chapters and all(chapter.mp3_file for chapter in chapters):
            self.manifest.status = BookStatus.COMPLETED
            self._save()


@app.command()
def generate(
    input_pdf: Annotated[
        Path,
        typer.Option("--input", exists=True, dir_okay=False, help="PDF file"),
    ],
    output: Annotated[
        Path, typer.Option("--output", help="Output folder for this book")
    ],
    from_stage: Annotated[
        FromStage,
        typer.Option("--from-stage", help="First stage to run"),
    ] = FromStage.EXTRACT,
    to_stage: Annotated[
        FromStage,
        typer.Option("--to-stage", help="Last stage to run"),
    ] = FromStage.MERGE,
    chapter: Annotated[
        int | None,
        typer.Option("--chapter", help="Limit stages to one chapter"),
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Rerun stages, ignoring cache")
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Log actions without side effects"),
    ] = False,
) -> None:
    """Run the audiobook pipeline for one PDF into an output folder."""
    if from_stage.stage > to_stage.stage:
        msg = (
            f"--from-stage ({from_stage.value}) must not come after "
            f"--to-stage ({to_stage.value})"
        )
        raise typer.BadParameter(msg)
    setup_logging(settings.app.log_level)
    pipeline = Pipeline(
        pdf_path=input_pdf.resolve(),
        paths=BookPaths(root=output),
        chapter_filter=chapter,
        force=force,
        dry_run=dry_run,
    )
    asyncio.run(pipeline.run(from_stage.stage, to_stage.stage))


if __name__ == "__main__":
    app()
