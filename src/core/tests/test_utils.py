import logging

import pytest

from core.utils import (
    INDEX_PAD_WIDTH,
    SLUG_MAX_LEN,
    chapter_dir_name,
    get_logger,
    padded_index,
    slugify,
)


@pytest.mark.parametrize(
    ("index", "expected"),
    [(0, "000"), (7, "007"), (42, "042"), (999, "999")],
)
def test_padded_index_pads_to_width(index: int, expected: str) -> None:
    assert padded_index(index) == expected


def test_padded_index_does_not_truncate_wide_values() -> None:
    assert padded_index(1234) == "1234"
    assert len("1234") > INDEX_PAD_WIDTH


def test_chapter_dir_name_uses_padded_index() -> None:
    assert chapter_dir_name(3) == "chapter_003"


def test_slugify_lowercases_and_joins_words() -> None:
    assert slugify("Hello World") == "hello_world"


def test_slugify_strips_punctuation() -> None:
    assert slugify("What's a Pyramid?!") == "whats_a_pyramid"


def test_slugify_collapses_separators_and_trims_edges() -> None:
    assert slugify("  a -- b__c  ") == "a_b_c"


def test_slugify_keeps_unicode_letters() -> None:
    assert slugify("Глава Первая") == "глава_первая"


def test_slugify_falls_back_to_untitled_when_empty() -> None:
    assert slugify("!!!") == "untitled"
    assert slugify("   ") == "untitled"


def test_slugify_truncates_to_max_len() -> None:
    result = slugify("a" * (SLUG_MAX_LEN + 20))
    assert len(result) == SLUG_MAX_LEN


def test_get_logger_returns_namespaced_logger() -> None:
    logger = get_logger("audiobook.core")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "audiobook.core"
