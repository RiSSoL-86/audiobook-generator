import re
from typing import final, override

from core.common.service import BaseService
from core.models.chapter import Chapter
from core.utils import slugify
from services.chapter.schemas import ChapterContent


@final
class ChapterService(BaseService):
    """Splits cleaned text into chapters, guided by the table of contents."""

    HEADING = re.compile(r"^\s*#{1,6}\s+(?P<title>.+?)\s*$")
    TOC_NUMBERED = re.compile(
        r"^\s*\d+\s+\*{0,2}(?P<title>.+?)\*{0,2}\s+(?P<page>\d+)\s*$"
    )
    TOC_NAMED = re.compile(
        r"^\s*\*{0,2}(?P<title>preface|introduction|references|foreword"
        r"|prologue|epilogue|afterword|index|acknowledge?ments?)\*{0,2}"
        r"\s+(?P<page>\d+)\s*$",
        re.IGNORECASE,
    )

    @override
    async def execute(self, clean_text: str) -> list[ChapterContent]:
        """Return chapters in reading order; no text is lost or duplicated."""
        lines = clean_text.split("\n")
        anchors = self._toc_anchors(lines=lines)
        bounds = self._match_bounds(lines=lines, anchors=anchors)
        if len(bounds) < 2:
            return self._fallback(lines=lines)
        return self._build(lines=lines, bounds=bounds)

    def _toc_anchors(self, lines: list[str]) -> list[tuple[str, int]]:
        """Parse ordered (title, page) chapter entries from the contents."""
        start = next(
            (i for i, line in enumerate(lines) if self._is_contents(line)),
            None,
        )
        if start is None:
            return []
        end = next(
            (
                i
                for i in range(start + 1, len(lines))
                if self.HEADING.match(lines[i])
                and not self._is_contents(lines[i])
            ),
            len(lines),
        )
        anchors: list[tuple[str, int]] = []
        for line in lines[start:end]:
            match = self.TOC_NUMBERED.match(line) or self.TOC_NAMED.match(line)
            if match:
                anchors.append(
                    (match.group("title").strip(), int(match.group("page")))
                )
        return anchors

    def _match_bounds(
        self, lines: list[str], anchors: list[tuple[str, int]]
    ) -> list[tuple[int, str, int]]:
        """Bind each TOC anchor to its first heading in the body, in order."""
        heads = [
            (i, self._norm(match.group("title")), match.group("title").strip())
            for i, line in enumerate(lines)
            if (match := self.HEADING.match(line))
        ]
        bounds: list[tuple[int, str, int]] = []
        cursor = 0
        for title, page in anchors:
            target = self._norm(title)
            hit = next(
                (h for h in heads if h[0] >= cursor and h[1] == target), None
            )
            if hit is None:
                continue
            bounds.append((hit[0], hit[2], page))
            cursor = hit[0] + 1
        return bounds

    def _build(
        self, lines: list[str], bounds: list[tuple[int, str, int]]
    ) -> list[ChapterContent]:
        """Slice body text between bounds into ordered chapters."""
        result: list[ChapterContent] = []
        index = 0
        preamble = "\n".join(lines[: bounds[0][0]]).strip()
        if preamble:
            index += 1
            result.append(
                self._make(index=index, title="Front matter", body=preamble)
            )
        ends = [*[start for start, _, _ in bounds[1:]], len(lines)]
        for (start, title, page), end in zip(bounds, ends, strict=True):
            body = "\n".join(lines[start + 1 : end]).strip()
            index += 1
            result.append(
                self._make(index=index, title=title, body=body, page=page)
            )
        return result

    def _fallback(self, lines: list[str]) -> list[ChapterContent]:
        """Split on top-level headings when no contents section is found."""
        heads = [
            i for i, line in enumerate(lines) if line.lstrip().startswith("# ")
        ]
        if not heads:
            body = "\n".join(lines).strip()
            return [self._make(index=1, title="Book", body=body)]
        result: list[ChapterContent] = []
        ends = [*heads[1:], len(lines)]
        for index, (start, end) in enumerate(zip(heads, ends, strict=True), 1):
            match = self.HEADING.match(lines[start])
            title = match.group("title") if match else lines[start].strip()
            body = "\n".join(lines[start + 1 : end]).strip()
            result.append(self._make(index=index, title=title, body=body))
        return result

    @staticmethod
    def _make(
        index: int, title: str, body: str, page: int | None = None
    ) -> ChapterContent:
        """Build a ChapterContent value object for one chapter."""
        chapter = Chapter(
            index=index,
            raw_title=title,
            slug=slugify(value=title),
            page_start=page,
        )
        return ChapterContent(chapter=chapter, body=body)

    def _is_contents(self, line: str) -> bool:
        """Whether a line is a heading titled 'Contents'."""
        match = self.HEADING.match(line)
        return match is not None and self._norm(match["title"]) == "contents"

    @staticmethod
    def _norm(title: str) -> str:
        """Normalize a title for matching: lowercase, punctuation to spaces."""
        return re.sub(r"[\W_]+", " ", title.lower()).strip()
