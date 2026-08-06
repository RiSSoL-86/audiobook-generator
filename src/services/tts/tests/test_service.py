from typing import TYPE_CHECKING, override

from core.models.chunk import Chunk, ChunkStatus
from services.tts.clients.base import TTSClient
from services.tts.schemas import TTSResult
from services.tts.service import TTSService

if TYPE_CHECKING:
    from collections.abc import Callable

    import pytest

    from core.models.chapter import Chapter
    from core.paths import BookPaths


class OkClient(TTSClient):
    """Always returns audio; counts how many times it was called."""

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    @override
    async def synthesize(self, text: str) -> TTSResult:
        self.calls += 1
        return TTSResult(audio=b"AUDIO", request_id="req-1")


class FailingClient(TTSClient):
    """Fails for the first ``fail_times`` calls, then returns audio."""

    def __init__(self, fail_times: int) -> None:
        super().__init__()
        self.fail_times = fail_times
        self.calls = 0

    @override
    async def synthesize(self, text: str) -> TTSResult:
        self.calls += 1
        if self.calls <= self.fail_times:
            msg = "provider unavailable"
            raise RuntimeError(msg)
        return TTSResult(audio=b"AUDIO", request_id="req-2")


def build_service(client: TTSClient, max_retries: int = 0) -> TTSService:
    """A TTSService wired to a stub client with a fixed retry budget."""
    service = TTSService()
    service.tts_client = client
    service.settings = service.settings.model_copy(
        update={
            "tts": service.settings.tts.model_copy(
                update={"max_retries": max_retries, "concurrency": 2}
            )
        }
    )
    return service


def write_chunk_text(
    paths: BookPaths, chapter_index: int, chunk_index: int, text: str
) -> None:
    """Create the on-disk chunk text file the TTS stage reads."""
    path = paths.chunk_file(chapter_index, chunk_index)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


async def test_voices_all_pending_chunks(
    book_paths: BookPaths,
    make_chapter: Callable[..., Chapter],
) -> None:
    chunks = [
        Chunk(index=1, chapter_index=1, char_count=5),
        Chunk(index=2, chapter_index=1, char_count=5),
    ]
    chapter = make_chapter(index=1, chunks=chunks)
    for chunk in chunks:
        write_chunk_text(book_paths, 1, chunk.index, "hello")
    progress: list[None] = []
    service = build_service(OkClient())

    await service.execute(
        chapter=chapter,
        paths=book_paths,
        on_progress=lambda: progress.append(None),
    )

    for chunk in chunks:
        audio = book_paths.chunk_audio_file(1, chunk.index)
        assert audio.read_bytes() == b"AUDIO"
        assert chunk.status is ChunkStatus.GENERATED
        assert chunk.request_id == "req-1"
    assert len(progress) == 2


async def test_skips_chunks_already_generated(
    book_paths: BookPaths,
    make_chapter: Callable[..., Chapter],
) -> None:
    chunk = Chunk(
        index=1, chapter_index=1, char_count=5, status=ChunkStatus.GENERATED
    )
    chapter = make_chapter(index=1, chunks=[chunk])
    audio = book_paths.chunk_audio_file(1, 1)
    audio.parent.mkdir(parents=True, exist_ok=True)
    audio.write_bytes(b"OLD")
    client = OkClient()
    service = build_service(client)

    await service.execute(chapter=chapter, paths=book_paths)

    assert client.calls == 0
    assert audio.read_bytes() == b"OLD"


async def test_marks_chunk_failed_after_exhausting_retries(
    book_paths: BookPaths,
    make_chapter: Callable[..., Chapter],
) -> None:
    chunk = Chunk(index=1, chapter_index=1, char_count=5)
    chapter = make_chapter(index=1, chunks=[chunk])
    write_chunk_text(book_paths, 1, 1, "hello")
    service = build_service(FailingClient(fail_times=5), max_retries=0)

    await service.execute(chapter=chapter, paths=book_paths)

    assert chunk.status is ChunkStatus.FAILED
    assert chunk.error == "provider unavailable"
    assert not book_paths.chunk_audio_file(1, 1).exists()


async def test_retries_then_succeeds(
    book_paths: BookPaths,
    make_chapter: Callable[..., Chapter],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", no_sleep)
    chunk = Chunk(index=1, chapter_index=1, char_count=5)
    chapter = make_chapter(index=1, chunks=[chunk])
    write_chunk_text(book_paths, 1, 1, "hello")
    client = FailingClient(fail_times=1)
    service = build_service(client, max_retries=2)

    await service.execute(chapter=chapter, paths=book_paths)

    assert client.calls == 2
    assert chunk.status is ChunkStatus.GENERATED
    assert chunk.error is None
    assert book_paths.chunk_audio_file(1, 1).read_bytes() == b"AUDIO"
