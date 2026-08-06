import asyncio
from typing import TYPE_CHECKING, Any

import pytest

from core.models.chunk import Chunk
from services.merge.service import MergeService

if TYPE_CHECKING:
    from collections.abc import Callable

    from core.models.chapter import Chapter
    from core.paths import BookPaths


class FakeProc:
    """A stand-in for an asyncio subprocess with canned output."""

    def __init__(
        self, returncode: int, stdout: bytes = b"", stderr: bytes = b""
    ) -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    async def communicate(self) -> tuple[bytes, bytes]:
        return self._stdout, self._stderr


def make_audio_files(paths: BookPaths, chapter_index: int, count: int) -> None:
    """Create ``count`` non-empty audio chunk files for a chapter."""
    for index in range(1, count + 1):
        audio = paths.chunk_audio_file(chapter_index, index)
        audio.parent.mkdir(parents=True, exist_ok=True)
        audio.write_bytes(b"MP3")


async def test_raises_when_chapter_has_no_chunks(
    book_paths: BookPaths,
    make_chapter: Callable[..., Chapter],
) -> None:
    chapter = make_chapter(index=1, chunks=[])
    with pytest.raises(RuntimeError, match="no chunks"):
        await MergeService().execute(chapter=chapter, paths=book_paths)


async def test_raises_when_audio_chunks_missing(
    book_paths: BookPaths,
    make_chapter: Callable[..., Chapter],
) -> None:
    chunk = Chunk(index=1, chapter_index=1, char_count=5)
    chapter = make_chapter(index=1, chunks=[chunk])
    with pytest.raises(RuntimeError, match="missing audio chunks"):
        await MergeService().execute(chapter=chapter, paths=book_paths)


async def test_merges_chunks_into_chapter_mp3(
    book_paths: BookPaths,
    make_chapter: Callable[..., Chapter],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    chunks = [Chunk(index=i, chapter_index=1, char_count=5) for i in (1, 2)]
    chapter = make_chapter(index=1, chunks=chunks)
    make_audio_files(book_paths, 1, 2)
    concat_files: list[Any] = []

    async def fake_concat(files: Any, output: Any) -> None:
        concat_files.extend(files)

    async def fake_probe(path: Any) -> float:
        return 12.5

    service = MergeService()
    monkeypatch.setattr(service, "_concat", fake_concat)
    monkeypatch.setattr(service, "_probe_duration", fake_probe)

    result = await service.execute(chapter=chapter, paths=book_paths)

    assert result.mp3_file == "001_chapter.mp3"
    assert result.duration_seconds == 12.5
    assert len(concat_files) == 2


async def test_concat_writes_list_then_cleans_it_up(
    book_paths: BookPaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    make_audio_files(book_paths, 1, 2)
    files = [book_paths.chunk_audio_file(1, i) for i in (1, 2)]
    output = book_paths.chapter_mp3_file(1, "chapter")
    output.parent.mkdir(parents=True, exist_ok=True)
    recorded: dict[str, Any] = {}

    async def fake_run(*cmd: str) -> None:
        recorded["cmd"] = cmd

    service = MergeService()
    monkeypatch.setattr(service, "_run", fake_run)

    await service._concat(files=files, output=output)

    assert not output.with_suffix(".txt").exists()
    assert str(output) in recorded["cmd"]
    assert service.settings.app.ffmpeg_path in recorded["cmd"]


async def test_run_raises_with_stderr_tail_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_exec(*args: Any, **kwargs: Any) -> FakeProc:
        return FakeProc(returncode=1, stderr=b"boom happened")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    with pytest.raises(RuntimeError, match="boom happened"):
        await MergeService()._run("ffmpeg", "-y")


async def test_probe_duration_parses_seconds(
    book_paths: BookPaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_exec(*args: Any, **kwargs: Any) -> FakeProc:
        return FakeProc(returncode=0, stdout=b"42.5\n")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    duration = await MergeService()._probe_duration(book_paths.root)
    assert duration == 42.5


async def test_probe_duration_returns_none_on_error(
    book_paths: BookPaths,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def fake_exec(*args: Any, **kwargs: Any) -> FakeProc:
        return FakeProc(returncode=1, stdout=b"")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    assert await MergeService()._probe_duration(book_paths.root) is None
