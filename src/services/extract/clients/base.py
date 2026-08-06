from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app_settings import settings
from core.utils import get_logger

if TYPE_CHECKING:
    from pathlib import Path


class ExtractClient(ABC):
    """Minimal PDF text extraction contract."""

    def __init__(self) -> None:
        self.settings = settings
        self.logger = get_logger(type(self).__name__)

    @abstractmethod
    async def extract(self, pdf_path: Path) -> str:
        """Return the raw extracted text of a PDF."""
        raise NotImplementedError
