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
    TOC_ENTRY = re.compile(
        r"^\s*#{0,6}\s*"
        r"(?:(?P<num>\d+)\s+)?"
        r"\*{0,2}(?P<title>.+?)\*{0,2}"
        r"[\s.]*\s"
        r"(?P<page>\d+|[ivxlcdm]+)\s*$",
        re.IGNORECASE,
    )
    PART = re.compile(r"^\s*#{0,6}\s*part\s+[ivxlcdm]+\b", re.IGNORECASE)
    CONTENTS_NOISE = re.compile(
        r"^\s*#{0,6}\s*(?:\d+|[ivxlcdm]+)?\s*"
        r"(?:contents|содержание|оглавление)\s*$",
        re.IGNORECASE,
    )
    NAMED = re.compile(
        r"^(?:preface|introduction|references|foreword|prologue"
        r"|epilog(?:ue)?|afterword|index|appendix|acknowledge?ments?"
        r"|введение|предисловие|послесловие|пролог|эпилог"
        r"|заключение|приложение|указатель)\b",
        re.IGNORECASE,
    )
    CONTENTS_TITLES = frozenset({"contents", "содержание", "оглавление"})
    HAS_LETTER = re.compile(r"[^\W\d_]", re.UNICODE)
    TOC_BREAK = 3

    @override
    async def execute(self, clean_text: str) -> list[ChapterContent]:
        """Return chapters in reading order; no text is lost or duplicated."""
        lines = clean_text.split("\n")
        span = self._contents_range(lines=lines)
        anchors = self._toc_anchors(lines=lines, span=span)
        bounds = self._match_bounds(lines=lines, anchors=anchors, span=span)
        if len(bounds) < 2:
            return self._fallback(lines=lines, span=span)
        return self._build(lines=lines, bounds=bounds, span=span)

    def _contents_range(self, lines: list[str]) -> tuple[int, int] | None:
        """Locate the contents block as a ``[start, end)`` line range."""
        cluster = self._densest_toc_cluster(lines)
        if cluster is None:
            return None
        start, end = cluster
        while start > 0 and not lines[start - 1].strip():
            start -= 1
        if start > 0 and self._is_toc_line(lines[start - 1]):
            start -= 1
        return start, end

    def _densest_toc_cluster(self, lines: list[str]) -> tuple[int, int] | None:
        """Return the front-half run richest in page-number lines."""
        clusters: list[tuple[int, int, int]] = []
        limit = len(lines) // 2
        i = 0
        while i < limit:
            if not self.TOC_ENTRY.match(lines[i]):
                i += 1
                continue
            last, breaks = i, 0
            j = i
            while j < len(lines):
                if self._is_toc_line(lines[j]):
                    last, breaks = j, 0
                elif lines[j].strip():
                    breaks += 1
                    if breaks >= self.TOC_BREAK:
                        break
                j += 1
            hits = sum(
                1 for k in range(i, last + 1) if self.TOC_ENTRY.match(lines[k])
            )
            clusters.append((hits, i, last + 1))
            i = last + 1
        if not clusters:
            return None
        hits, start, end = max(clusters, key=lambda c: (c[0], -c[1]))
        return start, end

    def _is_toc_line(self, line: str) -> bool:
        """Whether a line still belongs to the contents listing."""
        return bool(
            self.CONTENTS_NOISE.match(line)
            or self.PART.match(line)
            or self.TOC_ENTRY.match(line)
        )

    def _toc_anchors(
        self, lines: list[str], span: tuple[int, int] | None
    ) -> list[tuple[str, int | None]]:
        """Parse ordered top-level (title, page) entries from the contents."""
        if span is None:
            return []
        start, end = span
        anchors: list[tuple[str, int | None]] = []
        for line in lines[start:end]:
            match = self.TOC_ENTRY.match(line)
            if match is None:
                continue
            title = match.group("title").strip().strip("*").strip()
            if not title or self._norm(title) in self.CONTENTS_TITLES:
                continue
            if not self.HAS_LETTER.search(title):
                continue
            if match.group("num") is None and not self.NAMED.match(title):
                continue
            page = match.group("page")
            anchors.append((title, int(page) if page.isdigit() else None))
        return anchors

    def _match_bounds(
        self,
        lines: list[str],
        anchors: list[tuple[str, int | None]],
        span: tuple[int, int] | None,
    ) -> list[tuple[int, str, int | None]]:
        """Bind each TOC anchor to its first body heading, in order."""
        toc = range(span[0], span[1]) if span else range(0)
        heads = [
            (index, self._match_key(match.group("title")))
            for index, line in enumerate(lines)
            if index not in toc and (match := self.HEADING.match(line))
        ]
        bounds: list[tuple[int, str, int | None]] = []
        cursor = 0
        for title, page in anchors:
            target = self._match_key(title)
            named = self.NAMED.match(title) is not None
            for index, key in heads:
                if index < cursor:
                    continue
                if key == target or (
                    named and self._prefix_hit(head=key, full=target)
                ):
                    bounds.append((index, title, page))
                    cursor = index + 1
                    break
        return bounds

    @staticmethod
    def _prefix_hit(head: str, full: str) -> bool:
        """Whether a short named body heading opens a longer TOC entry."""
        return len(head.split()) >= 2 and full.startswith(f"{head} ")

    def _front_matter(
        self, lines: list[str], upto: int, span: tuple[int, int] | None
    ) -> str | None:
        """Text before ``upto`` minus the contents block; None if empty."""
        head = lines[:upto]
        if span is not None and span[1] <= upto:
            head = lines[: span[0]] + lines[span[1] : upto]
        return "\n".join(head).strip() or None

    def _build(
        self,
        lines: list[str],
        bounds: list[tuple[int, str, int | None]],
        span: tuple[int, int] | None,
    ) -> list[ChapterContent]:
        """Slice body text between bounds into ordered chapters."""
        result: list[ChapterContent] = []
        index = 0
        preamble = self._front_matter(
            lines=lines, upto=bounds[0][0], span=span
        )
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

    def _fallback(
        self, lines: list[str], span: tuple[int, int] | None
    ) -> list[ChapterContent]:
        """Split on top-level headings when no contents section is found."""
        heads = [
            i
            for i, line in enumerate(lines)
            if line.lstrip().startswith("# ") and not self._is_contents(line)
        ]
        if not heads:
            body = "\n".join(lines).strip()
            return [self._make(index=1, title="Book", body=body)]
        result: list[ChapterContent] = []
        index = 0
        preamble = self._front_matter(lines=lines, upto=heads[0], span=span)
        if preamble:
            index += 1
            result.append(
                self._make(index=index, title="Front matter", body=preamble)
            )
        ends = [*heads[1:], len(lines)]
        for start, end in zip(heads, ends, strict=True):
            match = self.HEADING.match(lines[start])
            title = match.group("title") if match else lines[start].strip()
            body = "\n".join(lines[start + 1 : end]).strip()
            index += 1
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
        """Whether a line is a heading titled 'Contents' (or a translation)."""
        match = self.HEADING.match(line)
        return (
            match is not None
            and self._norm(match["title"]) in self.CONTENTS_TITLES
        )

    @staticmethod
    def _norm(title: str) -> str:
        """Normalize a title for matching: lowercase, punctuation to spaces."""
        return re.sub(r"[\W_]+", " ", title.lower()).strip()

    def _match_key(self, title: str) -> str:
        """Normalize a heading, dropping leading/trailing page numbers."""
        norm = self._norm(title)
        norm = re.sub(r"^\d+\s+", "", norm)
        return re.sub(r"\s+\d+$", "", norm)
