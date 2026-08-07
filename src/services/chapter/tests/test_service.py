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
        "Preface",
        "Why a pyramid structure?",
        "The substructures",
    ]


async def test_chapters_are_indexed_and_carry_page_start() -> None:
    chapters = await ChapterService().execute(TOC_BOOK)
    assert [item.chapter.index for item in chapters] == [1, 2, 3]
    by_title = {item.chapter.raw_title: item.chapter for item in chapters}
    assert by_title["Why a pyramid structure?"].page_start == 5
    assert by_title["The substructures"].page_start == 17


async def test_body_is_sliced_between_headings() -> None:
    chapters = await ChapterService().execute(TOC_BOOK)
    bodies = {item.chapter.raw_title: item.body for item in chapters}
    assert bodies["Why a pyramid structure?"] == "Body of chapter one."
    assert bodies["The substructures"] == "Body of chapter two."


async def test_table_of_contents_is_never_narrated() -> None:
    # The contents listing must not leak into any chapter body.
    chapters = await ChapterService().execute(TOC_BOOK)
    for item in chapters:
        assert "# Contents" not in item.body
        assert "Why a pyramid structure?** 5" not in item.body


async def test_front_matter_kept_but_contents_block_removed() -> None:
    book = (
        "A Note to the Reader\n\nThis edition was revised.\n\n"
        "# Contents\n\nPreface 3\n1 **Only chapter** 5\n2 **Next** 9\n\n"
        "# Preface\n\nPreface body.\n\n"
        "# Only chapter\n\nBody one.\n\n# Next\n\nBody two.\n"
    )
    chapters = await ChapterService().execute(book)
    front = chapters[0]
    assert front.chapter.raw_title == "Front matter"
    assert "This edition was revised." in front.body
    assert "# Contents" not in front.body
    assert "Only chapter** 5" not in front.body


async def test_falls_back_to_top_level_headings_without_contents() -> None:
    text = "# Chapter One\n\nAlpha.\n\n# Chapter Two\n\nBeta."
    chapters = await ChapterService().execute(text)
    assert [item.chapter.raw_title for item in chapters] == [
        "Chapter One",
        "Chapter Two",
    ]
    assert chapters[0].body == "Alpha."
    assert chapters[1].body == "Beta."


async def test_fallback_keeps_front_matter_and_hides_contents() -> None:
    # TOC titles that don't match any body heading force the fallback path;
    # it must still drop the contents listing and keep the front matter.
    book = (
        "Opening note.\n\n"
        "# Contents\n\nAlpha 5\nBeta 9\n\n"
        "# Totally Different\n\nBody a.\n\n"
        "# Another One\n\nBody b.\n"
    )
    chapters = await ChapterService().execute(book)
    titles = [item.chapter.raw_title for item in chapters]
    assert titles == ["Front matter", "Totally Different", "Another One"]
    joined = "\n".join(item.body for item in chapters)
    assert "Opening note." in chapters[0].body
    assert "# Contents" not in joined
    assert "Alpha 5" not in joined


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
