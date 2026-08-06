from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from app_settings import settings
from core.utils import get_logger

if TYPE_CHECKING:
    from services.tts.schemas import TTSResult


class TTSClient(ABC):
    """Minimal text-to-speech client contract."""

    def __init__(self) -> None:
        self.settings = settings
        self.logger = get_logger(type(self).__name__)

    @abstractmethod
    async def synthesize(self, text: str) -> TTSResult:
        """Return synthesized audio for one text block."""
        raise NotImplementedError
