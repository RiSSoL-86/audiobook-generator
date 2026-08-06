import logging

from rich.logging import RichHandler


def setup_logging(level: str = "INFO") -> None:
    """Configure Rich-backed logging once for the whole app."""
    logging.basicConfig(
        level=level.upper(),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)],
    )
