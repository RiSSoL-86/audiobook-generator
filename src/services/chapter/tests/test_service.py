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


# A LlamaParse-style textbook TOC: chapter entries rendered as headings,
# Roman front-matter pages, dotted sub-sections and PART dividers to ignore,
# then a noisy body where running headers repeat titles and page numbers lead
# headings -- the shape that used to explode into hundreds of chapters.
TEXTBOOK = """\
Title Page

# CONTENTS

FOREWORD xv

## 1 Systems Engineering 1

1.1 Definitions of Key Terms, 2

1.2 Approach to this Chapter, 4

PART I FUNDAMENTALS 49

3 System Attributes 51

3.1 Definition of Key Terms, 51

INDEX 821

# FOREWORD

Foreword body.

# 1 SYSTEMS ENGINEERING

Chapter one body.

# 2 SYSTEMS ENGINEERING

More chapter one, page two running header.

# 62 SYSTEM ATTRIBUTES

Chapter three body.

# INDEX

Index body.
"""


async def test_textbook_toc_ignores_sections_headers_and_page_numbers() -> (
    None
):
    chapters = await ChapterService().execute(TEXTBOOK)
    titles = [item.chapter.raw_title for item in chapters]
    # Front matter, the two named entries, two numbered chapters -- no
    # sub-sections (1.1, 3.1), PART dividers, or per-page running headers.
    assert titles == [
        "Front matter",
        "FOREWORD",
        "Systems Engineering",
        "System Attributes",
        "INDEX",
    ]
    by_title = {item.chapter.raw_title: item for item in chapters}
    assert by_title["Systems Engineering"].chapter.page_start == 1
    assert by_title["System Attributes"].chapter.page_start == 51
    # The running-header page ("page two") stays inside chapter one's body.
    assert "page two running header" in by_title["Systems Engineering"].body
    # The contents listing is never narrated.
    for item in chapters:
        assert "# CONTENTS" not in item.body
        assert "PART I FUNDAMENTALS" not in item.body


# A real-world defect: the parser split the contents across pages and put the
# '# CONTENTS' heading in the MIDDLE of the listing, while the top of the list
# (chapters 1-2) sat above it. A copyright page's printer line ('10 9 8 7')
# also looks like a numbered entry. Anchoring on the word 'Contents' lost the
# early chapters; anchoring on the page-number run recovers them.
SPLIT_TOC_BOOK = """\
Title Page

10 9 8 7

1 First Chapter 5
2 Second Chapter 9

# CONTENTS

3 Third Chapter 21
4 Fourth Chapter 33

# First Chapter

Body one.

# Second Chapter

Body two.

# Third Chapter

Body three.

# Fourth Chapter

Body four.
"""


async def test_contents_split_around_heading_keeps_all_chapters() -> None:
    chapters = await ChapterService().execute(SPLIT_TOC_BOOK)
    titles = [item.chapter.raw_title for item in chapters]
    # No chapter is swallowed into front matter; the printer line is ignored.
    assert titles == [
        "Front matter",
        "First Chapter",
        "Second Chapter",
        "Third Chapter",
        "Fourth Chapter",
    ]
    for item in chapters:
        assert "# CONTENTS" not in item.body
        assert "First Chapter 5" not in item.body
        assert "10 9 8 7" not in item.body
