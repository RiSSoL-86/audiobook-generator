from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app_settings import settings
from core.utils import get_logger

if TYPE_CHECKING:
    from services.translate.schemas import TranslateResult


class TranslateClient(ABC):
    """Minimal text translation contract."""

    def __init__(self) -> None:
        self.settings = settings
        self.logger = get_logger(type(self).__name__)

    @abstractmethod
    async def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> TranslateResult:
        """Return the translation of one markdown block."""
        raise NotImplementedError
