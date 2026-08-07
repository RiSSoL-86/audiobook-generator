import re
from typing import final, override

from core.common.service import BaseService
from core.models.chunk import Chunk
from services.chunk.schemas import ChunkContent


@final
class ChunkService(BaseService):
    """Splits a chapter body into TTS blocks along paragraph boundaries."""

    PARAGRAPH_SPLIT = re.compile(r"\n\s*\n")
    SENTENCE_SPLIT = re.compile(r"(?<=[.!?…])\s+")
    PARAGRAPH_JOIN = "\n\n"

    MD_BOLD = re.compile(r"\*\*(?!\s)(.+?)(?<!\s)\*\*")
    MD_ITALIC = re.compile(r"\*(?!\s)(.+?)(?<!\s)\*")
    MD_HEADING = re.compile(r"(?m)^[ \t]*#{1,6}[ \t]*")
    MD_BLOCKQUOTE = re.compile(r"(?m)^[ \t]*>[ \t]?")

    @override
    async def execute(
        self, body: str, chapter_index: int
    ) -> list[ChunkContent]:
        """Return ordered, non-empty blocks within the configured limits."""
        blocks = self._pack(atoms=self._atoms(body=body))
        return [
            ChunkContent(
                chunk=Chunk(
                    index=position,
                    chapter_index=chapter_index,
                    char_count=len(text),
                ),
                text=text,
            )
            for position, text in enumerate(blocks, start=1)
        ]

    def _atoms(self, body: str) -> list[str]:
        """Split into paragraphs, then sentences, then hard-wrap by words."""
        body = self.MD_BOLD.sub(r"\1", body)
        body = self.MD_ITALIC.sub(r"\1", body)
        body = self.MD_HEADING.sub("", body)
        body = self.MD_BLOCKQUOTE.sub("", body)
        atoms: list[str] = []
        for raw in self.PARAGRAPH_SPLIT.split(body):
            paragraph = raw.strip()
            if not paragraph:
                continue
            units = (
                [paragraph]
                if len(paragraph) <= self.settings.chunk.hard_max_chars
                else self._split_sentences(paragraph=paragraph)
            )
            for unit in units:
                atoms.extend(self._hard_wrap(unit=unit))
        return atoms

    def _hard_wrap(self, unit: str) -> list[str]:
        """Last-resort split on word boundaries to honor the hard cap."""
        cap = self.settings.chunk.hard_max_chars
        if len(unit) <= cap:
            return [unit]
        words: list[str] = []
        for word in unit.split():
            while len(word) > cap:
                words.append(word[:cap])
                word = word[cap:]
            words.append(word)
        pieces: list[str] = []
        current = ""
        for word in words:
            candidate = word if not current else f"{current} {word}"
            if len(candidate) <= cap:
                current = candidate
            else:
                pieces.append(current)
                current = word
        if current:
            pieces.append(current)
        return pieces

    def _split_sentences(self, paragraph: str) -> list[str]:
        """Group sentences into units within the hard character cap."""
        groups: list[str] = []
        current = ""
        for raw in self.SENTENCE_SPLIT.split(paragraph):
            sentence = raw.strip()
            if not sentence:
                continue
            if not current:
                current = sentence
            elif len(current) + 1 + len(sentence) <= (
                self.settings.chunk.hard_max_chars
            ):
                current = f"{current} {sentence}"
            else:
                groups.append(current)
                current = sentence
        if current:
            groups.append(current)
        return groups

    def _pack(self, atoms: list[str]) -> list[str]:
        """Greedily pack atoms toward the target size, never splitting one."""
        blocks: list[str] = []
        current = ""
        for atom in atoms:
            if not current:
                current = atom
                continue
            candidate = f"{current}{self.PARAGRAPH_JOIN}{atom}"
            if self._fits(current=current, candidate=candidate):
                current = candidate
            else:
                blocks.append(current)
                current = atom
        if current:
            blocks.append(current)
        return blocks

    def _fits(self, current: str, candidate: str) -> bool:
        """Whether the candidate merge stays within size targets."""
        if len(candidate) <= self.settings.chunk.target_max_chars:
            return True
        return (
            len(current) < self.settings.chunk.target_min_chars
            and len(candidate) <= self.settings.chunk.hard_max_chars
        )
