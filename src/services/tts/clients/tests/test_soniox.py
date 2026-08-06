from typing import Any

import pytest
from pydantic import SecretStr

from app_settings.tts import TTSSettings
from services.tts.clients.soniox import SonioxTTSClient


def with_key(client: SonioxTTSClient, key: str | None) -> None:
    """Point the client at settings carrying the given API key."""
    client.settings = client.settings.model_copy(
        update={
            "tts": TTSSettings(
                soniox_api_key=SecretStr(key) if key else None,
                model="tts-model",
                voice="narrator",
            )
        }
    )


async def test_synthesize_requires_api_key() -> None:
    client = SonioxTTSClient()
    with_key(client, None)
    with pytest.raises(ValueError, match="SONIOX_API_KEY"):
        await client.synthesize(text="hello")


async def test_synthesize_posts_and_returns_audio(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeResponse:
        content = b"AUDIO-BYTES"

        def __init__(self) -> None:
            self.headers = {"x-request-id": "req-123"}

        def raise_for_status(self) -> None:
            captured["raised"] = True

    class FakeAsyncClient:
        async def __aenter__(self) -> FakeAsyncClient:
            return self

        async def __aexit__(self, *exc: object) -> bool:
            return False

        async def post(self, **kwargs: Any) -> FakeResponse:
            captured.update(kwargs)
            return FakeResponse()

    monkeypatch.setattr(
        "services.tts.clients.soniox.httpx.AsyncClient", FakeAsyncClient
    )
    client = SonioxTTSClient()
    with_key(client, "secret-key")

    result = await client.synthesize(text="Read this aloud.")

    assert result.audio == b"AUDIO-BYTES"
    assert result.request_id == "req-123"
    assert captured["url"] == SonioxTTSClient.ENDPOINT
    assert captured["headers"]["Authorization"] == "Bearer secret-key"
    assert captured["json"]["text"] == "Read this aloud."
    assert captured["json"]["model"] == "tts-model"
    assert captured["raised"] is True
