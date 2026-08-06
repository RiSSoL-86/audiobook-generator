from services.chapter.service import ChapterService

TOC_BOOK = """\
# Contents

Preface 3
1 **Why a pyramid structure?** 5
2 **The substructures** 17

# Preface

Preface body.

# Why a pyramid structure?

Body of chapter one.

# The substructures

Body of chapter two.
"""


async def test_splits_by_table_of_contents() -> None:
    chapters = await ChapterService().execute(TOC_BOOK)
    titles = [item.chapter.raw_title for item in chapters]
    assert titles == [
        "Front matter",
        "Preface",
        "Why a pyramid structure?",
        "The substructures",
    ]


async def test_chapters_are_indexed_and_carry_page_start() -> None:
    chapters = await ChapterService().execute(TOC_BOOK)
    assert [item.chapter.index for item in chapters] == [1, 2, 3, 4]
    by_title = {item.chapter.raw_title: item.chapter for item in chapters}
    assert by_title["Why a pyramid structure?"].page_start == 5
    assert by_title["The substructures"].page_start == 17
    assert by_title["Front matter"].page_start is None


async def test_body_is_sliced_between_headings() -> None:
    chapters = await ChapterService().execute(TOC_BOOK)
    bodies = {item.chapter.raw_title: item.body for item in chapters}
    assert bodies["Why a pyramid structure?"] == "Body of chapter one."
    assert bodies["The substructures"] == "Body of chapter two."
    assert "# Contents" in bodies["Front matter"]


async def test_falls_back_to_top_level_headings_without_contents() -> None:
    text = "# Chapter One\n\nAlpha.\n\n# Chapter Two\n\nBeta."
    chapters = await ChapterService().execute(text)
    assert [item.chapter.raw_title for item in chapters] == [
        "Chapter One",
        "Chapter Two",
    ]
    assert chapters[0].body == "Alpha."
    assert chapters[1].body == "Beta."


async def test_single_chapter_when_no_headings_at_all() -> None:
    text = "Just some prose.\n\nNo headings here."
    chapters = await ChapterService().execute(text)
    assert len(chapters) == 1
    assert chapters[0].chapter.raw_title == "Book"
    assert chapters[0].body == text


async def test_slug_is_derived_from_title() -> None:
    chapters = await ChapterService().execute(TOC_BOOK)
    by_title = {item.chapter.raw_title: item.chapter for item in chapters}
    chapter = by_title["Why a pyramid structure?"]
    assert chapter.slug == "why_a_pyramid_structure"
