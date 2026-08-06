import re
from typing import final, override

from core.common.service import BaseService


@final
class CleanService(BaseService):
    """Cleans extracted text: dehyphenation and running-noise removal."""

    HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
    HTML_TAG = re.compile(r"<[^>]+>")
    MD_TABLE_ROW = re.compile(r"^[ \t]*\|.*$\n?", re.MULTILINE)
    NO_CONTENT = re.compile(r"NO_CONTENT_HERE")
    TRAILING_WS = re.compile(r"[ \t]+\n")
    MULTI_BLANK = re.compile(r"\n{3,}")

    REPEAT_THRESHOLD = 5
    SHORT_LINE_LEN = 60

    @override
    async def execute(self, raw_text: str) -> str:
        """Return cleaned Markdown text ready for chapter splitting."""
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        text = self.HYPHEN_BREAK.sub(r"\1\2", text)
        text = self.HTML_TAG.sub("", text)
        text = self.MD_TABLE_ROW.sub("", text)
        text = self.NO_CONTENT.sub("", text)

        # Drop short lines that repeat like running headers or footers.
        lines = text.split("\n")
        counts: dict[str, int] = {}
        for line in lines:
            key = line.strip()
            if key and len(key) <= self.SHORT_LINE_LEN:
                counts[key] = counts.get(key, 0) + 1
        repeated = {
            key
            for key, count in counts.items()
            if count >= self.REPEAT_THRESHOLD
        }
        text = "\n".join(
            line for line in lines if line.strip() not in repeated
        )

        text = self.TRAILING_WS.sub("\n", text)
        text = self.MULTI_BLANK.sub("\n\n", text)
        return text.strip() + "\n"
