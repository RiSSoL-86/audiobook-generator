from typing import TYPE_CHECKING, final, override

from llama_cloud import AsyncLlamaCloud

from services.extract.clients.base import ExtractClient

if TYPE_CHECKING:
    from pathlib import Path


@final
class LlamaCloudExtractClient(ExtractClient):
    """PDF text extraction via LlamaParse (LlamaCloud)."""

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
                output_options={
                    "markdown": {"tables": {"output_tables_as_markdown": True}}
                },
            )
        return response.markdown_full or ""
