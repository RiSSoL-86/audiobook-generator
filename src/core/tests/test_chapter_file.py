from core.chapter_file import read_body, render_chapter


def test_render_chapter_writes_title_heading_then_body() -> None:
    assert render_chapter("Intro", "Body text") == "# Intro\n\nBody text\n"


def test_read_body_drops_leading_title_heading() -> None:
    text = render_chapter("Intro", "Body text")
    assert read_body(text) == "Body text"


def test_read_body_keeps_text_without_heading() -> None:
    assert read_body("Just a paragraph.") == "Just a paragraph."


def test_read_body_drops_indented_heading() -> None:
    assert read_body("   # Title\nBody") == "Body"


def test_read_body_strips_surrounding_whitespace() -> None:
    assert read_body("# Title\n\n\nBody\n\n") == "Body"


def test_read_body_of_empty_text_is_empty() -> None:
    assert read_body("") == ""


def test_render_then_read_body_round_trips() -> None:
    body = "First line.\n\nSecond line."
    assert read_body(render_chapter("Chapter", body)) == body
