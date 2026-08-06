from core.models.book import BookStatus


def test_book_status_values() -> None:
    assert BookStatus.PENDING.value == "pending"
    assert BookStatus.TEXT_EXTRACTED.value == "text_extracted"
    assert BookStatus.CHAPTERS_READY.value == "chapters_ready"
    assert BookStatus.AUDIO_GENERATED.value == "audio_generated"
    assert BookStatus.COMPLETED.value == "completed"


def test_book_status_is_string_enum() -> None:
    assert isinstance(BookStatus.PENDING, str)
    assert BookStatus("completed") is BookStatus.COMPLETED
