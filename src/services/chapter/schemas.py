from typing import final

from core.models.chapter import Chapter
from services.common.schema import Schema


@final
class ChapterContent(Schema):
    """A detected chapter paired with its body text."""

    chapter: Chapter
    body: str
