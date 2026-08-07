from app_settings.chunk import ChunkSettings
from services.chunk.service import ChunkService


def build_service(
    target_min: int = 10, target_max: int = 20, hard_max: int = 30
) -> ChunkService:
    """A ChunkService with small, deterministic size targets."""
    service = ChunkService()
    service.settings = service.settings.model_copy(
        update={
            "chunk": ChunkSettings(
                target_min_chars=target_min,
                target_max_chars=target_max,
                hard_max_chars=hard_max,
            )
        }
    )
    return service


async def test_empty_body_yields_no_chunks() -> None:
    chunks = await build_service().execute(body="   \n\n  ", chapter_index=1)
    assert chunks == []


async def test_single_short_paragraph_is_one_chunk() -> None:
    service = build_service()
    chunks = await service.execute(body="Hello world.", chapter_index=2)
    assert len(chunks) == 1
    assert chunks[0].text == "Hello world."
    assert chunks[0].chunk.index == 1
    assert chunks[0].chunk.chapter_index == 2
    assert chunks[0].chunk.char_count == len("Hello world.")


async def test_small_paragraphs_are_packed_together() -> None:
    service = build_service()
    chunks = await service.execute(body="Hello.\n\nWorld.", chapter_index=1)
    assert len(chunks) == 1
    assert chunks[0].text == "Hello.\n\nWorld."


async def test_paragraphs_split_when_exceeding_target() -> None:
    body = f"{'a' * 15}\n\n{'b' * 15}"
    chunks = await build_service().execute(body=body, chapter_index=1)
    assert [chunk.text for chunk in chunks] == ["a" * 15, "b" * 15]


async def test_long_word_is_hard_wrapped_to_cap() -> None:
    chunks = await build_service().execute(body="x" * 70, chapter_index=1)
    assert [chunk.chunk.char_count for chunk in chunks] == [30, 30, 10]


async def test_indexes_are_sequential_and_counts_match_text() -> None:
    body = "\n\n".join(f"Paragraph number {n} here." for n in range(6))
    chunks = await build_service().execute(body=body, chapter_index=7)
    assert [chunk.chunk.index for chunk in chunks] == list(
        range(1, len(chunks) + 1)
    )
    for chunk in chunks:
        assert chunk.chunk.chapter_index == 7
        assert chunk.chunk.char_count == len(chunk.text)


async def test_no_chunk_exceeds_hard_cap() -> None:
    body = " ".join("Sentence about pyramids." for _ in range(50))
    chunks = await build_service().execute(body=body, chapter_index=1)
    assert chunks
    assert all(chunk.chunk.char_count <= 30 for chunk in chunks)


async def test_strips_markdown_heading_markers() -> None:
    body = "# System Engineering\n\n## Analysis, Design"
    chunks = await build_service(hard_max=60, target_max=60).execute(
        body=body, chapter_index=1
    )
    text = "\n\n".join(chunk.text for chunk in chunks)
    assert "#" not in text
    assert "System Engineering" in text
    assert "Analysis, Design" in text


async def test_strips_emphasis_and_blockquote_markers() -> None:
    body = "A **bold** and *italic* word.\n\n> A quoted line."
    chunks = await build_service(hard_max=80, target_max=80).execute(
        body=body, chapter_index=1
    )
    text = "\n\n".join(chunk.text for chunk in chunks)
    assert "*" not in text
    assert ">" not in text
    assert "A bold and italic word." in text
    assert "A quoted line." in text


async def test_keeps_bare_asterisk_in_prose() -> None:
    chunks = await build_service(hard_max=80, target_max=80).execute(
        body="Compute 2 * 3 for the result.", chapter_index=1
    )
    assert chunks[0].text == "Compute 2 * 3 for the result."
