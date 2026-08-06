import logging

from rich.logging import RichHandler

from core.logging import setup_logging


def test_setup_logging_sets_level_and_rich_handler() -> None:
    root = logging.getLogger()
    original_level = root.level
    original_handlers = root.handlers[:]
    try:
        root.handlers = []
        setup_logging("debug")
        assert root.level == logging.DEBUG
        assert any(isinstance(h, RichHandler) for h in root.handlers)
    finally:
        root.setLevel(original_level)
        root.handlers = original_handlers
