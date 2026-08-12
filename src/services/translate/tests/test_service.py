from typing import override

import pytest

from services.translate.clients.base import TranslateClient
from services.translate.schemas import TranslateResult
from services.translate.service import TranslateService


class OkClient(TranslateClient):
    """Always returns a translation; counts how many times it was called."""

    def __init__(self) -> None:
        super().__init__()
        self.calls = 0

    @override
    async def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> TranslateResult:
        self.calls += 1
        return TranslateResult(
            text=f"{target_lang}:{text}", request_id="req-1"
        )


class FailingClient(TranslateClient):
    """Fails for the first ``fail_times`` calls, then returns a translation."""

    def __init__(self, fail_times: int) -> None:
        super().__init__()
        self.fail_times = fail_times
        self.calls = 0

    @override
    async def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> TranslateResult:
        self.calls += 1
        if self.calls <= self.fail_times:
            msg = "provider unavailable"
            raise RuntimeError(msg)
        return TranslateResult(text=f"ok:{text}", request_id="req-2")


def build_service(
    client: TranslateClient,
    max_retries: int = 0,
    batch_max_chars: int = 6000,
) -> TranslateService:
    """A TranslateService wired to a stub client with a fixed retry budget."""
    service = TranslateService()
    service.translate_client = client
    service.settings = service.settings.model_copy(
        update={
            "translate": service.settings.translate.model_copy(
                update={
                    "max_retries": max_retries,
                    "target_lang": "ru",
                    "batch_max_chars": batch_max_chars,
                }
            )
        }
    )
    return service


async def test_translates_text() -> None:
    client = OkClient()
    service = build_service(client)

    result = await service._translate_text(text="# Title\n\nHello")

    assert result == "ru:# Title\n\nHello"
    assert client.calls == 1


async def test_splits_long_chapter_into_paragraph_batches() -> None:
    client = OkClient()
    # A cap that fits one paragraph but not two forces one batch each.
    service = build_service(client, batch_max_chars=12)

    result = await service._translate_text(
        text="# Heading\n\nAlpha body.\n\nBeta body."
    )

    assert client.calls == 3
    assert result == "ru:# Heading\n\nru:Alpha body.\n\nru:Beta body."


async def test_retries_then_succeeds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def no_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("asyncio.sleep", no_sleep)
    client = FailingClient(fail_times=1)
    service = build_service(client, max_retries=2)

    result = await service._translate_text(text="Hello")

    assert result == "ok:Hello"
    assert client.calls == 2


async def test_raises_after_exhausting_retries() -> None:
    service = build_service(FailingClient(fail_times=5), max_retries=0)

    with pytest.raises(RuntimeError, match="provider unavailable"):
        await service._translate_text(text="Hello")
