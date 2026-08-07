import re
from typing import final, override

from core.common.service import BaseService


@final
class CleanService(BaseService):
    """Cleans extracted text: dehyphenation and page-furniture removal."""

    HYPHEN_BREAK = re.compile(r"(\w)-\n(\w)")
    HTML_TAG = re.compile(r"</?[A-Za-z][A-Za-z0-9-]*(?:\s+[^<>]*?)?/?>")
    MD_TABLE_ROW = re.compile(r"^[ \t]*\|.*$\n?", re.MULTILINE)
    NO_CONTENT = re.compile(r"NO_CONTENT_HERE")
    TRAILING_WS = re.compile(r"[ \t]+\n")
    MULTI_BLANK = re.compile(r"\n{3,}")

    ARABIC_LINE = re.compile(r"^\s*(\d{1,4})\s*$")
    NUMERAL_LINE = re.compile(
        r"^\s*(?:\d{1,3}-\d{1,3}|[ivxlcdm]{2,7}|[IVXLCDM]{2,7})\s*$"
    )
    HEADING = re.compile(r"^\s*#{1,6}\s+(?P<text>.+?)\s*$")
    CAPS_HEADING_PAGE = re.compile(
        r"^(?P<head>\s*#{1,6}\s+[^a-z\n]*[A-Z][^a-z\n]*?)\s+\d{1,4}\s*$"
    )
    LOWERCASE = re.compile(r"[a-z]")
    HAS_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)

    REPEAT_THRESHOLD = 5
    RUNHEAD_THRESHOLD = 2
    SHORT_LINE_LEN = 60
    MIN_PAGE_RUN = 5

    @override
    async def execute(self, raw_text: str) -> str:
        """Return cleaned Markdown text ready for chapter splitting."""
        text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        text = self.HYPHEN_BREAK.sub(r"\1\2", text)
        text = self.HTML_TAG.sub("", text)
        text = self.MD_TABLE_ROW.sub("", text)
        text = self.NO_CONTENT.sub("", text)

        lines = [
            self.CAPS_HEADING_PAGE.sub(r"\g<head>", line)
            for line in text.split("\n")
        ]

        furniture = self._repeated_furniture(lines)
        running = self._repeated_running_headers(lines)
        pages = self._page_number_lines(lines)

        seen_running: set[str] = set()
        kept: list[str] = []
        for index, line in enumerate(lines):
            key = line.strip()
            if index in pages or self.NUMERAL_LINE.match(line):
                continue
            if key in furniture:
                continue
            if key in running:
                if key in seen_running:
                    continue
                seen_running.add(key)
            kept.append(line)
        text = "\n".join(kept)

        text = self.TRAILING_WS.sub("\n", text)
        text = self.MULTI_BLANK.sub("\n\n", text)
        return text.strip() + "\n"

    def _page_number_lines(self, lines: list[str]) -> set[int]:
        """Indices of standalone integers that form the ascending page run."""
        accepted: list[int] = []
        last = 0
        for index, line in enumerate(lines):
            match = self.ARABIC_LINE.match(line)
            if match is None:
                continue
            value = int(match.group(1))
            if value > last:
                accepted.append(index)
                last = value
        return set(accepted) if len(accepted) >= self.MIN_PAGE_RUN else set()

    def _repeated_furniture(self, lines: list[str]) -> set[str]:
        """Short non-heading lines that recur like running headers/footers."""
        counts: dict[str, int] = {}
        for line in lines:
            key = line.strip()
            if key.startswith("#"):
                continue
            if key and len(key) <= self.SHORT_LINE_LEN:
                counts[key] = counts.get(key, 0) + 1
        return {
            key
            for key, count in counts.items()
            if count >= self.REPEAT_THRESHOLD
        }

    def _repeated_running_headers(self, lines: list[str]) -> set[str]:
        """All-caps headings that recur: running headers, not real chapters."""
        counts: dict[str, int] = {}
        for line in lines:
            match = self.HEADING.match(line)
            if match is None:
                continue
            text = match.group("text")
            if self.LOWERCASE.search(text) or not self.HAS_LETTER.search(text):
                continue
            key = line.strip()
            counts[key] = counts.get(key, 0) + 1
        return {
            key
            for key, count in counts.items()
            if count >= self.RUNHEAD_THRESHOLD
        }
