from abc import ABC, abstractmethod
from typing import Any

from app_settings import settings
from core.utils import get_logger


class BaseService(ABC):
    """Base class for application services."""

    def __init__(self) -> None:
        self.settings = settings
        self.logger = get_logger(type(self).__name__)

    @abstractmethod
    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Run the service business operation."""
        raise NotImplementedError
