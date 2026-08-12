from typing import TYPE_CHECKING, ClassVar, override

import pytest
from typer.testing import CliRunner

import main
from app_settings import settings
from core.manifest import ManifestRepository
from core.models.book import BookStatus
from core.models.chapter import Chapter
from core.models.chunk import Chunk, ChunkStatus
from core.models.manifest import BookManifest
from core.models.stage import Stage
from core.paths import BookPaths
from services.chapter.schemas import ChapterContent
from services.chunk.schemas import ChunkContent
from services.merge.schemas import MergeResult
from services.tts.clients.base import TTSClient
from services.tts.schemas import TTSResult

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


def make_pipeline(
    tmp_path: Path,
    *,
    force: bool = False,
    dry_run: bool = False,
    chapter: int | None = None,
    translate: bool = False,
) -> main.Pipeline:
    """A Pipeline rooted in a temp dir with a placeholder PDF."""
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    return main.Pipeline(
        pdf_path=pdf,
        paths=BookPaths(root=tmp_path / "out"),
        chapter_filter=chapter,
        force=force,
        dry_run=dry_run,
        translate=translate,
    )


def seed_manifest(paths: BookPaths, chapters: list[Chapter]) -> None:
    """Persist a manifest with pre-detected chapters."""
    ManifestRepository(path=paths.manifest_file).save(
        BookManifest(source_file="book.pdf", slug="book", chapters=chapters)
    )


class FakeChapterService:
    """Yields two fixed chapters regardless of the input text."""

    async def execute(self, clean_text: str) -> list[ChapterContent]:
        return [
            ChapterContent(
                chapter=Chapter(index=1, raw_title="One", slug="one"),
                body="Alpha body.",
            ),
            ChapterContent(
                chapter=Chapter(index=2, raw_title="Two", slug="two"),
                body="Beta body.",
            ),
        ]


class FakeChunkService:
    """Splits every chapter body into a single chunk; records the calls."""

    chunked: ClassVar[list[int]] = []

    async def execute(
        self, body: str, chapter_index: int
    ) -> list[ChunkContent]:
        type(self).chunked.append(chapter_index)
        chunk = Chunk(
            index=1, chapter_index=chapter_index, char_count=len(body)
        )
        return [ChunkContent(chunk=chunk, text=body)]


class FakeTTSService:
    """Writes audio and marks each chunk generated, no network involved."""

    async def execute(
        self,
        chapter: Chapter,
        paths: BookPaths,
        on_progress: Callable[[], None] | None = None,
    ) -> None:
        for chunk in chapter.chunks:
            audio = paths.chunk_audio_file(chapter.index, chunk.index)
            audio.parent.mkdir(parents=True, exist_ok=True)
            audio.write_bytes(b"AUDIO")
            chunk.status = ChunkStatus.GENERATED
        if on_progress is not None:
            on_progress()


def test_existing_manifest_is_reused_even_with_force(tmp_path: Path) -> None:
    # Regression: --force must re-run stages, never discard the manifest.
    paths = BookPaths(root=tmp_path / "out")
    seed_manifest(paths, [Chapter(index=1, raw_title="One", slug="one")])

    pipeline = make_pipeline(tmp_path, force=True)

    assert [c.index for c in pipeline.manifest.chapters] == [1]


def test_fresh_run_starts_from_empty_manifest(tmp_path: Path) -> None:
    pipeline = make_pipeline(tmp_path)
    assert pipeline.manifest.chapters == []
    assert pipeline.manifest.source_file == "book.pdf"


async def test_run_executes_only_selected_stage_range(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pipeline = make_pipeline(tmp_path)
    ran: list[str] = []

    async def record(name: str) -> None:
        ran.append(name)

    monkeypatch.setattr(pipeline, "_stage_extract", lambda: record("extract"))
    monkeypatch.setattr(
        pipeline, "_stage_chapters", lambda: record("chapters")
    )
    monkeypatch.setattr(pipeline, "_stage_chunks", lambda: record("chunks"))
    monkeypatch.setattr(pipeline, "_stage_tts", lambda: record("tts"))
    monkeypatch.setattr(pipeline, "_stage_merge", lambda: record("merge"))

    await pipeline.run(Stage.CHAPTERS, Stage.CHUNK)

    assert ran == ["chapters", "chunks"]


async def test_tts_from_stage_with_force_preserves_chapters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = BookPaths(root=tmp_path / "out")
    chunk = Chunk(index=1, chapter_index=1, char_count=5)
    seed_manifest(
        paths,
        [Chapter(index=1, raw_title="One", slug="one", chunks=[chunk])],
    )
    text = paths.chunk_file(1, 1)
    text.parent.mkdir(parents=True, exist_ok=True)
    text.write_text("hello", encoding="utf-8")
    monkeypatch.setattr(main, "TTSService", FakeTTSService)

    pipeline = make_pipeline(tmp_path, force=True)
    await pipeline.run(Stage.TTS, Stage.TTS)

    assert [c.index for c in pipeline.manifest.chapters] == [1]
    assert pipeline.manifest.chapters[0].chunks[0].status is (
        ChunkStatus.GENERATED
    )
    assert paths.chunk_audio_file(1, 1).read_bytes() == b"AUDIO"


async def test_chunk_force_removes_stale_chunk_and_audio(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = BookPaths(root=tmp_path / "out")
    chapter = Chapter(index=1, raw_title="One", slug="one")
    seed_manifest(paths, [chapter])
    # A body for the chunk stage to split, plus stale leftovers from before.
    chapter_md = paths.chapter_file(1)
    chapter_md.parent.mkdir(parents=True, exist_ok=True)
    chapter_md.write_text("# One\n\nBody.", encoding="utf-8")
    stale_chunk = paths.chunk_file(1, 9)
    stale_chunk.parent.mkdir(parents=True, exist_ok=True)
    stale_chunk.write_text("orphan", encoding="utf-8")
    stale_audio = paths.chunk_audio_file(1, 9)
    stale_audio.parent.mkdir(parents=True, exist_ok=True)
    stale_audio.write_bytes(b"OLD")
    monkeypatch.setattr(main, "ChunkService", FakeChunkService)

    pipeline = make_pipeline(tmp_path, force=True)
    await pipeline.run(Stage.CHUNK, Stage.CHUNK)

    assert not stale_chunk.exists()
    assert not stale_audio.exists()
    assert paths.chunk_file(1, 1).exists()


class FakeTranslateService:
    """Prefixes the markdown instead of calling OpenAI; records the calls."""

    translated: ClassVar[list[str]] = []

    async def execute(
        self,
        chapters: list[Chapter],
        paths: BookPaths,
        force: bool = False,
    ) -> None:
        for chapter in chapters:
            output = paths.chapter_translated_file(chapter.index)
            if output.exists() and not force:
                continue
            text = paths.chapter_file(chapter.index).read_text(
                encoding="utf-8"
            )
            type(self).translated.append(text)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(f"RU:\n{text}", encoding="utf-8")


async def test_translate_stage_writes_file_and_chunk_reads_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    FakeTranslateService.translated.clear()
    FakeChunkService.chunked.clear()
    paths = BookPaths(root=tmp_path / "out")
    chapter = Chapter(index=1, raw_title="One", slug="one")
    ManifestRepository(path=paths.manifest_file).save(
        BookManifest(
            source_file="book.pdf",
            slug="book",
            settings=settings.to_snapshot(),
            chapters=[chapter],
        )
    )
    chapter_md = paths.chapter_file(1)
    chapter_md.parent.mkdir(parents=True, exist_ok=True)
    chapter_md.write_text("# One\n\nBody.", encoding="utf-8")
    monkeypatch.setattr(main, "TranslateService", FakeTranslateService)
    monkeypatch.setattr(main, "ChunkService", FakeChunkService)

    pipeline = make_pipeline(tmp_path, translate=True)
    await pipeline.run(Stage.TRANSLATE, Stage.CHUNK)

    translated = paths.chapter_translated_file(1)
    assert translated.read_text(encoding="utf-8") == "RU:\n# One\n\nBody."
    assert FakeTranslateService.translated == ["# One\n\nBody."]
    # The chunk stage must consume the translated body, not the original.
    assert paths.chunk_file(1, 1).read_text(encoding="utf-8") == (
        "RU:\n# One\n\nBody."
    )
    # The run records what it translated in the manifest settings snapshot.
    snapshot = pipeline.manifest.settings
    assert snapshot is not None
    assert snapshot.translate is not None
    assert snapshot.translate.target_lang == settings.translate.target_lang


async def test_translate_stage_skipped_without_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths = BookPaths(root=tmp_path / "out")
    seed_manifest(paths, [Chapter(index=1, raw_title="One", slug="one")])
    chapter_md = paths.chapter_file(1)
    chapter_md.parent.mkdir(parents=True, exist_ok=True)
    chapter_md.write_text("# One\n\nBody.", encoding="utf-8")

    def boom() -> FakeTranslateService:
        msg = "translate must not run without --translate"
        raise AssertionError(msg)

    monkeypatch.setattr(main, "TranslateService", boom)

    pipeline = make_pipeline(tmp_path, translate=False)
    await pipeline.run(Stage.TRANSLATE, Stage.TRANSLATE)

    assert not paths.chapter_translated_file(1).exists()


async def test_dry_run_writes_no_manifest(tmp_path: Path) -> None:
    pipeline = make_pipeline(tmp_path, dry_run=True)
    await pipeline.run(Stage.EXTRACT, Stage.MERGE)
    assert not pipeline.paths.manifest_file.exists()


RESUME_BOOK = (
    "# Chapter One\n\nAlpha body text.\n\n# Chapter Two\n\nboom body text.\n"
)


class FakeExtractService:
    """Returns fixed Markdown instead of calling the real parser."""

    calls: ClassVar[int] = 0

    async def execute(self, pdf_path: Path) -> str:
        type(self).calls += 1
        return RESUME_BOOK


class ToggleTTSClient(TTSClient):
    """Fails on any chunk containing 'boom' while ``fail`` is set."""

    fail = True
    voiced: ClassVar[list[str]] = []

    @override
    async def synthesize(self, text: str) -> TTSResult:
        if type(self).fail and "boom" in text:
            msg = "provider down"
            raise RuntimeError(msg)
        type(self).voiced.append(text)
        return TTSResult(audio=b"AUDIO", request_id="req")


class FakeMergeService:
    """Writes a placeholder MP3 and reports a fixed duration."""

    merged: ClassVar[list[int]] = []

    async def execute(self, chapter: Chapter, paths: BookPaths) -> MergeResult:
        type(self).merged.append(chapter.index)
        output = paths.chapter_mp3_file(chapter.index, chapter.slug)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"MP3")
        return MergeResult(mp3_file=output.name, duration_seconds=1.0)


class CrashOnceExtract(FakeExtractService):
    """Fails the first time it is armed, then extracts normally."""

    armed: ClassVar[bool] = False

    @override
    async def execute(self, pdf_path: Path) -> str:
        if type(self).armed:
            type(self).armed = False
            msg = "extract boom"
            raise RuntimeError(msg)
        return await super().execute(pdf_path)


class CrashOnceChapters(FakeChapterService):
    """Fails the first time it is armed, then splits normally."""

    armed: ClassVar[bool] = False

    @override
    async def execute(self, clean_text: str) -> list[ChapterContent]:
        if type(self).armed:
            type(self).armed = False
            msg = "chapters boom"
            raise RuntimeError(msg)
        return await super().execute(clean_text)


class CrashChunkOnChapterTwo(FakeChunkService):
    """Fails on chapter two the first time it is armed, then chunks it."""

    armed: ClassVar[bool] = False

    @override
    async def execute(
        self, body: str, chapter_index: int
    ) -> list[ChunkContent]:
        if type(self).armed and chapter_index == 2:
            type(self).armed = False
            msg = "chunk boom"
            raise RuntimeError(msg)
        return await super().execute(body, chapter_index)


class CrashMergeOnChapterTwo(FakeMergeService):
    """Fails on chapter two the first time it is armed, then merges it."""

    armed: ClassVar[bool] = False

    @override
    async def execute(self, chapter: Chapter, paths: BookPaths) -> MergeResult:
        if type(self).armed and chapter.index == 2:
            type(self).armed = False
            msg = "merge boom"
            raise RuntimeError(msg)
        return await super().execute(chapter, paths)


def wire_fakes(
    monkeypatch: pytest.MonkeyPatch,
    *,
    extract: type = FakeExtractService,
    chapters: type = FakeChapterService,
    chunk: type = FakeChunkService,
    tts: type = FakeTTSService,
    merge: type = FakeMergeService,
) -> None:
    """Swap every pipeline service for a deterministic in-memory fake."""
    monkeypatch.setattr(main, "ExtractService", extract)
    monkeypatch.setattr(main, "ChapterService", chapters)
    monkeypatch.setattr(main, "ChunkService", chunk)
    monkeypatch.setattr(main, "TTSService", tts)
    monkeypatch.setattr(main, "MergeService", merge)
    FakeExtractService.calls = 0
    FakeChunkService.chunked = []
    FakeMergeService.merged = []


async def test_full_run_resumes_after_failure_on_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Mirrors: run the command, it dies mid-way, run the SAME command again
    # and it picks up exactly where it stopped -- no work is redone.
    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", no_sleep)
    monkeypatch.setattr(main, "ExtractService", FakeExtractService)
    monkeypatch.setattr(main, "MergeService", FakeMergeService)
    monkeypatch.setattr(
        "services.tts.service.SonioxTTSClient", ToggleTTSClient
    )
    ToggleTTSClient.fail = True
    ToggleTTSClient.voiced = []

    # First run: chapter two's audio fails, everything else is persisted.
    first = make_pipeline(tmp_path)
    await first.run(Stage.EXTRACT, Stage.MERGE)

    paths = first.paths
    ch_one, ch_two = first.manifest.chapters
    assert ch_one.chunks[0].status is ChunkStatus.GENERATED
    assert ch_two.chunks[0].status is ChunkStatus.FAILED
    assert ch_one.mp3_file is not None
    assert ch_two.mp3_file is None
    assert first.manifest.status is not BookStatus.COMPLETED

    # Second run of the identical command, now with the provider healthy.
    ToggleTTSClient.fail = False
    ToggleTTSClient.voiced = []
    second = make_pipeline(tmp_path)
    await second.run(Stage.EXTRACT, Stage.MERGE)

    ch_one, ch_two = second.manifest.chapters
    assert ch_one.chunks[0].status is ChunkStatus.GENERATED
    assert ch_two.chunks[0].status is ChunkStatus.GENERATED
    assert ch_one.mp3_file is not None
    assert ch_two.mp3_file is not None
    assert second.manifest.status is BookStatus.COMPLETED
    # Only the previously-failed chunk is re-voiced; done work is not redone.
    assert ToggleTTSClient.voiced == ["boom body text."]
    assert paths.chunk_audio_file(2, 1).read_bytes() == b"AUDIO"


async def test_resumes_when_extract_fails_on_first_step(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Crash on step 1: nothing is persisted, so the rerun starts clean.
    wire_fakes(monkeypatch, extract=CrashOnceExtract)
    CrashOnceExtract.armed = True

    first = make_pipeline(tmp_path)
    with pytest.raises(RuntimeError, match="extract boom"):
        await first.run(Stage.EXTRACT, Stage.MERGE)
    assert not first.paths.full_text_file.exists()
    assert not first.paths.manifest_file.exists()

    second = make_pipeline(tmp_path)
    await second.run(Stage.EXTRACT, Stage.MERGE)

    assert second.manifest.status is BookStatus.COMPLETED
    assert [c.index for c in second.manifest.chapters] == [1, 2]


async def test_resumes_when_chapters_fail_after_extract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Crash on step 2: the extracted text survives and is not re-parsed.
    wire_fakes(monkeypatch, chapters=CrashOnceChapters)
    CrashOnceChapters.armed = True

    first = make_pipeline(tmp_path)
    with pytest.raises(RuntimeError, match="chapters boom"):
        await first.run(Stage.EXTRACT, Stage.MERGE)
    assert first.paths.full_text_file.exists()
    assert first.manifest.status is BookStatus.TEXT_EXTRACTED
    assert first.manifest.chapters == []

    FakeExtractService.calls = 0
    second = make_pipeline(tmp_path)
    await second.run(Stage.EXTRACT, Stage.MERGE)

    assert FakeExtractService.calls == 0  # extract skipped on the rerun
    assert second.manifest.status is BookStatus.COMPLETED
    assert [c.index for c in second.manifest.chapters] == [1, 2]


async def test_resumes_when_chunk_fails_midway(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Crash halfway through step 3: chapter one's chunks are kept.
    wire_fakes(monkeypatch, chunk=CrashChunkOnChapterTwo)
    CrashChunkOnChapterTwo.armed = True

    first = make_pipeline(tmp_path)
    with pytest.raises(RuntimeError, match="chunk boom"):
        await first.run(Stage.EXTRACT, Stage.CHUNK)
    ch_one, ch_two = first.manifest.chapters
    assert ch_one.chunks
    assert not ch_two.chunks

    FakeChunkService.chunked = []
    second = make_pipeline(tmp_path)
    await second.run(Stage.EXTRACT, Stage.MERGE)

    assert FakeChunkService.chunked == [2]  # only chapter two re-chunked
    ch_one, ch_two = second.manifest.chapters
    assert ch_one.chunks and ch_two.chunks
    assert second.manifest.status is BookStatus.COMPLETED


async def test_resumes_when_merge_fails_midway(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Crash halfway through step 5: chapter one's MP3 is kept.
    wire_fakes(monkeypatch, merge=CrashMergeOnChapterTwo)
    CrashMergeOnChapterTwo.armed = True

    first = make_pipeline(tmp_path)
    with pytest.raises(RuntimeError, match="merge boom"):
        await first.run(Stage.EXTRACT, Stage.MERGE)
    ch_one, ch_two = first.manifest.chapters
    assert ch_one.mp3_file is not None
    assert (first.paths.mp3_dir / ch_one.mp3_file).exists()
    assert ch_two.mp3_file is None

    FakeMergeService.merged = []
    second = make_pipeline(tmp_path)
    await second.run(Stage.EXTRACT, Stage.MERGE)

    assert FakeMergeService.merged == [2]  # chapter one not re-merged
    ch_one, ch_two = second.manifest.chapters
    assert ch_one.mp3_file is not None
    assert ch_two.mp3_file is not None
    assert second.manifest.status is BookStatus.COMPLETED


def test_generate_rejects_inverted_stage_range(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    result = CliRunner().invoke(
        main.app,
        [
            "--input",
            str(pdf),
            "--output",
            str(tmp_path / "out"),
            "--from-stage",
            "merge",
            "--to-stage",
            "extract",
        ],
    )
    assert result.exit_code == 2
