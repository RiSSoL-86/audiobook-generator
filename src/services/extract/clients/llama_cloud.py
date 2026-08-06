from typing import TYPE_CHECKING, final, override

from llama_cloud import AsyncLlamaCloud

from services.extract.clients.base import ExtractClient

if TYPE_CHECKING:
    from pathlib import Path


@final
class LlamaCloudExtractClient(ExtractClient):
    """PDF text extraction via LlamaParse (LlamaCloud)."""

    PROMPT = (
        "Extract only the main body text and its headings. Do not transcribe, "
        "describe, or caption any non-text content such as images, icons, "
        "logos, decorative graphics, drop caps, or figures. Remove all page "
        "furniture wherever it appears in the top or bottom margin: running "
        "headers and footers, marginal notes, edge marks, and page numbers in "
        "any form -- Arabic (12), Roman (xii, XII), or compound (12-1). "
        "Front-matter Roman-numeral page numbers must be removed as well. A "
        "short line that is only a page number is never body text. Keep "
        "headings as real text. Leave empty or non-text regions empty; never "
        "emit any placeholder token (for example NO_CONTENT_HERE) for them -- "
        "simply omit such regions."
    )

    @override
    async def extract(self, pdf_path: Path) -> str:
        """Return the raw extracted text of the whole PDF."""
        key = self.settings.extract.llama_cloud_api_key
        if key is None:
            msg = "EXTRACT_LLAMA_CLOUD_API_KEY is required"
            raise ValueError(msg)
        async with AsyncLlamaCloud(api_key=key.get_secret_value()) as client:
            response = await client.parsing.parse(
                upload_file=pdf_path,
                tier="cost_effective",
                version="latest",
                expand=["markdown_full"],
                agentic_options={"custom_prompt": self.PROMPT},
                processing_options={"ignore": {"ignore_text_in_image": True}},
                output_options={
                    "markdown": {"tables": {"output_tables_as_markdown": True}}
                },
            )
        return response.markdown_full or ""
