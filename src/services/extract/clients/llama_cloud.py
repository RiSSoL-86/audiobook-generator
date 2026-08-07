from typing import TYPE_CHECKING, final, override

import httpx
from llama_cloud import AsyncLlamaCloud

from services.extract.clients.base import ExtractClient

if TYPE_CHECKING:
    from pathlib import Path


@final
class LlamaCloudExtractClient(ExtractClient):
    """PDF text extraction via LlamaParse (LlamaCloud)."""

    TIMEOUT = httpx.Timeout(timeout=600.0, connect=5.0)

    PROMPT = (
        "Extract only the main body text and its headings. Do not transcribe, "
        "describe, or caption any non-text content such as images, icons, "
        "logos, decorative graphics, drop caps, or figures. Remove all page "
        "furniture wherever it appears in the top or bottom margin: running "
        "headers and footers, marginal notes, edge marks, and page numbers in "
        "any form -- Arabic (12), Roman (xii, XII), or compound (12-1). "
        "Front-matter Roman-numeral page numbers must be removed as well. A "
        " short line that is only a page number is never body text. Leave "
        "empty or non-text regions empty; never emit any placeholder token "
        "(for example NO_CONTENT_HERE) for them -- simply omit such regions.\n"
        "\n"
        "Assign heading levels by the book's structure, not by font size:\n"
        "- Use a level-1 heading (#) ONLY at the point where a top-level "
        "division of the book begins: a numbered chapter, a named part, or a "
        "front/back-matter section such as Foreword, Preface, Introduction, "
        "Appendix, Glossary, Bibliography, or Index. Emit each such heading "
        "exactly once, at the place where that division actually starts in "
        "the body.\n"
        "- Use level-2/level-3 headings (##, ###) for sections and subsections"
        " inside a chapter (for example 3.1, 3.1.1).\n"
        "- NEVER turn any of these into a heading of any level: a running "
        "header or footer repeated across pages, a page number, a table or "
        "figure caption (for example TABLE 3.2, FIGURE 4.1), or an entry in "
        "the table of contents. A text fragment that reappears on many pages "
        "is page furniture, not a heading.\n"
        "\n"
        "Keep the book's title and any genuine front matter (title page, "
        "author, epigraph, dedication, foreword, preface, introduction). But "
        "omit the table of contents entirely: the list of chapter titles "
        "paired with page numbers near the start of the book must not appear "
        "in the output at all, since it only duplicates the real chapter "
        "headings in the body."
    )

    @override
    async def extract(self, pdf_path: Path) -> str:
        """Return the raw extracted text of the whole PDF."""
        key = self.settings.extract.llama_cloud_api_key
        if key is None:
            msg = "EXTRACT_LLAMA_CLOUD_API_KEY is required"
            raise ValueError(msg)
        async with AsyncLlamaCloud(
            api_key=key.get_secret_value(), timeout=self.TIMEOUT
        ) as client:
            response = await client.parsing.parse(
                upload_file=pdf_path,
                tier="cost_effective",
                version="latest",
                expand=["markdown"],
                agentic_options={"custom_prompt": self.PROMPT},
                processing_options={"ignore": {"ignore_text_in_image": True}},
                output_options={
                    "markdown": {"tables": {"output_tables_as_markdown": True}}
                },
            )
        if response.markdown_full:
            return response.markdown_full
        markdown = getattr(response, "markdown", None)
        pages = getattr(markdown, "pages", None) or []
        return "\n\n".join(
            page.markdown for page in pages if getattr(page, "markdown", None)
        )
