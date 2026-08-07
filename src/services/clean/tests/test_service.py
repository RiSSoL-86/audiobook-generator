from services.clean.service import CleanService


async def test_dehyphenates_line_broken_words() -> None:
    result = await CleanService().execute("recon-\nstruct the sen-\ntence")
    assert "reconstruct" in result
    assert "sentence" in result


async def test_strips_html_tags() -> None:
    text = "A <b>bold</b> and <i>italic</i> word"
    result = await CleanService().execute(text)
    assert result.strip() == "A bold and italic word"


async def test_keeps_angle_brackets_in_prose() -> None:
    # The tag stripper must not eat comparison operators in ordinary text.
    text = "If a < 5 and b > 3 then stop."
    result = await CleanService().execute(text)
    assert result.strip() == "If a < 5 and b > 3 then stop."


async def test_removes_markdown_table_rows() -> None:
    text = "Before\n\n| a | b |\n| - | - |\n\nAfter"
    result = await CleanService().execute(text)
    assert "|" not in result
    assert "Before" in result
    assert "After" in result


async def test_removes_no_content_here_placeholder() -> None:
    text = "Real paragraph.\n\nNO_CONTENT_HERE\n\nMore real text."
    result = await CleanService().execute(text)
    assert "NO_CONTENT_HERE" not in result
    assert "Real paragraph." in result
    assert "More real text." in result


async def test_drops_repeated_running_headers() -> None:
    header = "THE PYRAMID PRINCIPLE"
    body = "\n\n".join([header, "Body one", header, "Body two", header])
    text = "\n\n".join([body, header, header])  # header appears 5 times
    result = await CleanService().execute(text)
    assert header not in result
    assert "Body one" in result
    assert "Body two" in result


async def test_keeps_repeated_headings() -> None:
    heading = "# Summary"
    parts = [heading, "a", heading, "b", heading, "c", heading, "d", heading]
    result = await CleanService().execute("\n\n".join(parts))
    assert result.count(heading) == 5


async def test_keeps_short_lines_below_repeat_threshold() -> None:
    text = "\n\n".join(["Keep me", "other", "Keep me"])  # only twice
    result = await CleanService().execute(text)
    assert result.count("Keep me") == 2


async def test_keeps_standalone_numbers_in_body() -> None:
    # The value-based page-number cut was removed; real numbers must survive.
    text = "In the year\n\n1984\n\nsomething happened."
    result = await CleanService().execute(text)
    assert "1984" in result


async def test_normalizes_newlines_and_collapses_blank_lines() -> None:
    text = "First\r\n\r\n\r\n\r\nSecond"
    result = await CleanService().execute(text)
    assert "\r" not in result
    assert result == "First\n\nSecond\n"


async def test_output_is_stripped_with_single_trailing_newline() -> None:
    result = await CleanService().execute("  \n\nContent  \n  \n")
    assert result == "Content\n"
