from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr

from services.translate.clients import openai as openai_module
from services.translate.clients.openai import OpenAITranslateClient


def build_client(api_key: str | None) -> OpenAITranslateClient:
    """An OpenAI client whose settings carry the given key (or none)."""
    client = OpenAITranslateClient()
    secret = None if api_key is None else SecretStr(api_key)
    client.settings = client.settings.model_copy(
        update={
            "translate": client.settings.translate.model_copy(
                update={"openai_api_key": secret}
            )
        }
    )
    return client


async def test_missing_key_fails_fast() -> None:
    client = build_client(None)

    with pytest.raises(ValueError, match="TRANSLATE_OPENAI_API_KEY"):
        await client.translate(
            text="Hello", source_lang="en", target_lang="ru"
        )


async def test_connects_directly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeHttpClient:
        def __init__(self, **kwargs: Any) -> None:
            captured["trust_env"] = kwargs.get("trust_env")

        async def aclose(self) -> None:
            captured["closed"] = True

    class FakeOpenAI:
        def __init__(self, **kwargs: Any) -> None:
            captured["http_client"] = kwargs.get("http_client")

        async def __aenter__(self) -> FakeOpenAI:
            return self

        async def __aexit__(self, *_: object) -> bool:
            return False

        @property
        def chat(self) -> Any:
            async def create(**_: Any) -> Any:
                message = SimpleNamespace(content="perevod")
                choice = SimpleNamespace(message=message)
                return SimpleNamespace(choices=[choice], id="req-9")

            return SimpleNamespace(completions=SimpleNamespace(create=create))

    monkeypatch.setattr(
        "services.translate.clients.openai.httpx.AsyncClient", FakeHttpClient
    )
    monkeypatch.setattr(openai_module, "AsyncOpenAI", FakeOpenAI)
    client = build_client("sk-test")

    result = await client.translate(
        text="Hello", source_lang="en", target_lang="ru"
    )

    assert result.text == "perevod"
    assert captured["trust_env"] is True
    assert captured["http_client"] is not None
    assert captured["closed"] is True


async def test_echoed_source_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeOpenAI:
        def __init__(self, **_: Any) -> None:
            pass

        async def __aenter__(self) -> FakeOpenAI:
            return self

        async def __aexit__(self, *_: object) -> bool:
            return False

        @property
        def chat(self) -> Any:
            async def create(*, messages: Any, **_: Any) -> Any:
                echo = messages[-1]["content"]  # return the source verbatim
                choice = SimpleNamespace(message=SimpleNamespace(content=echo))
                return SimpleNamespace(choices=[choice], id="req-echo")

            return SimpleNamespace(completions=SimpleNamespace(create=create))

    monkeypatch.setattr(openai_module, "AsyncOpenAI", FakeOpenAI)
    client = build_client("sk-test")

    with pytest.raises(RuntimeError, match="echoed the source"):
        await client.translate(
            text="Hello world", source_lang="en", target_lang="ru"
        )
