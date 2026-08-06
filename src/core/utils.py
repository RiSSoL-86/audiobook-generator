import logging
import re
import unicodedata

INDEX_PAD_WIDTH = 3
SLUG_MAX_LEN = 60

_STRIP_CHARS = re.compile(r"[^\w\s-]", re.UNICODE)
_SEPARATORS = re.compile(r"[\s_-]+", re.UNICODE)


def padded_index(index: int) -> str:
    """Zero-pad an index to the on-disk width, e.g. ``7`` -> ``007``."""
    return f"{index:0{INDEX_PAD_WIDTH}d}"


def chapter_dir_name(index: int) -> str:
    """Per-chapter directory name, e.g. ``chapter_001``."""
    return f"chapter_{padded_index(index)}"


def slugify(value: str) -> str:
    """Build a filesystem-safe slug, keeping Unicode letters."""
    text = unicodedata.normalize("NFKC", value).strip().lower()
    text = _STRIP_CHARS.sub("", text)
    text = _SEPARATORS.sub("_", text).strip("_")
    return text[:SLUG_MAX_LEN] or "untitled"


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced application logger."""
    return logging.getLogger(name)
