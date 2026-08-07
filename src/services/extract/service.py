from typing import TYPE_CHECKING, final, override

from core.common.service import BaseService
from services.extract.clients.llama_cloud import LlamaCloudExtractClient

if TYPE_CHECKING:
    from pathlib import Path

    from services.extract.clients.base import ExtractClient


@final
class ExtractService(BaseService):
    """Extracts raw text from a PDF via a pluggable extraction client."""

    def __init__(self) -> None:
        super().__init__()
        self.extract_client: ExtractClient = LlamaCloudExtractClient()

    @override
    async def execute(self, pdf_path: Path) -> str:
        """Return the raw extracted text of the whole PDF."""
        return await self.extract_client.extract(pdf_path)
