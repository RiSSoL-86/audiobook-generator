from typing import Any, final, override

import pytest

from app_settings import settings
from core.common.service import BaseService


def test_base_service_cannot_be_instantiated() -> None:
    with pytest.raises(TypeError):
        BaseService()  # type: ignore[abstract]


@final
class EchoService(BaseService):
    @override
    async def execute(self, *args: Any, **kwargs: Any) -> str:
        return "done"


def test_subclass_gets_settings_and_named_logger() -> None:
    service = EchoService()
    assert service.settings is settings
    assert service.logger.name == "EchoService"


async def test_subclass_execute_runs() -> None:
    assert await EchoService().execute() == "done"
