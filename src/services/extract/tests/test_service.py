from pathlib import Path
from typing import override

from services.extract.clients.base import ExtractClient
from services.extract.service import ExtractService


class StubExtractClient(ExtractClient):
    """Records the PDF it was asked to extract and returns fixed text."""

    def __init__(self) -> None:
        super().__init__()
        self.seen: Path | None = None

    @override
    async def extract(self, pdf_path: Path) -> str:
        self.seen = pdf_path
        return "extracted text"


async def test_service_delegates_to_client() -> None:
    service = ExtractService()
    client = StubExtractClient()
    service.extract_client = client
    pdf = Path("book.pdf")

    result = await service.execute(pdf)

    assert result == "extracted text"
    assert client.seen == pdf
