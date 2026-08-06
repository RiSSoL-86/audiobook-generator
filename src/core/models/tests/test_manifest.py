from datetime import UTC, datetime

from core.models.book import BookStatus
from core.models.chapter import Chapter
from core.models.manifest import (
    BookManifest,
    MergeSnapshot,
    ProcessingSettings,
    TTSSnapshot,
)


def make_settings() -> ProcessingSettings:
    return ProcessingSettings(
        tts=TTSSnapshot(
            model="soniox-1",
            voice="voice-1",
            language="en",
            speed=1.0,
            audio_format="mp3",
        ),
        merge=MergeSnapshot(bitrate="128k", sample_rate=44100),
    )


def test_defaults() -> None:
    manifest = BookManifest(source_file="book.pdf", slug="book")
    assert manifest.status is BookStatus.PENDING
    assert manifest.started_at is None
    assert manifest.settings is None
    assert manifest.chapters == []


def test_round_trips_through_camel_case_json() -> None:
    manifest = BookManifest(
        source_file="book.pdf",
        slug="book",
        status=BookStatus.TEXT_EXTRACTED,
        started_at=datetime(2026, 8, 6, tzinfo=UTC),
        settings=make_settings(),
        chapters=[Chapter(index=1, raw_title="Intro", slug="intro")],
    )
    payload = manifest.model_dump_json(by_alias=True)
    assert '"sourceFile"' in payload
    assert '"sampleRate"' in payload

    loaded = BookManifest.model_validate_json(payload)
    assert loaded == manifest
    assert loaded.settings is not None
    assert loaded.settings.merge.sample_rate == 44100
