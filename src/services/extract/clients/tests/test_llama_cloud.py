from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import SecretStr

from app_settings.extract import ExtractSettings
from services.extract.clients import llama_cloud
from services.extract.clients.llama_cloud import LlamaCloudExtractClient


def with_key(client: LlamaCloudExtractClient, key: str | None) -> None:
    """Point the client at settings carrying the given API key."""
    client.settings = client.settings.model_copy(
        update={
            "extract": ExtractSettings(
                llama_cloud_api_key=SecretStr(key) if key else None
            )
        }
    )


async def test_extract_requires_api_key() -> None:
    client = LlamaCloudExtractClient()
    with_key(client, None)
    with pytest.raises(ValueError, match="LLAMA_CLOUD_API_KEY"):
        await client.extract(Path("book.pdf"))


async def test_extract_calls_llamaparse_and_returns_markdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    class FakeParsing:
        async def parse(self, **kwargs: Any) -> SimpleNamespace:
            captured.update(kwargs)
            return SimpleNamespace(markdown_full="# Extracted body")

    class FakeClient:
        parsing = FakeParsing()

    class FakeLlamaCloud:
        def __init__(self, *, api_key: str) -> None:
            captured["api_key"] = api_key

        async def __aenter__(self) -> FakeClient:
            return FakeClient()

        async def __aexit__(self, *exc: object) -> bool:
            return False

    monkeypatch.setattr(llama_cloud, "AsyncLlamaCloud", FakeLlamaCloud)
    client = LlamaCloudExtractClient()
    with_key(client, "secret-key")

    result = await client.extract(Path("book.pdf"))

    assert result == "# Extracted body"
    assert captured["api_key"] == "secret-key"
    assert captured["upload_file"] == Path("book.pdf")
    assert captured["expand"] == ["markdown"]
    prompt = captured["agentic_options"]["custom_prompt"]
    assert prompt == LlamaCloudExtractClient.PROMPT


async def test_extract_stitches_pages_when_no_markdown_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeParsing:
        async def parse(self, **kwargs: Any) -> SimpleNamespace:
            pages = SimpleNamespace(
                pages=[
                    SimpleNamespace(markdown="# One"),
                    SimpleNamespace(markdown="Body two"),
                ]
            )
            return SimpleNamespace(markdown_full=None, markdown=pages)

    class FakeClient:
        parsing = FakeParsing()

    class FakeLlamaCloud:
        def __init__(self, *, api_key: str) -> None:
            pass

        async def __aenter__(self) -> FakeClient:
            return FakeClient()

        async def __aexit__(self, *exc: object) -> bool:
            return False

    monkeypatch.setattr(llama_cloud, "AsyncLlamaCloud", FakeLlamaCloud)
    client = LlamaCloudExtractClient()
    with_key(client, "secret-key")

    assert await client.extract(Path("book.pdf")) == "# One\n\nBody two"


async def test_extract_returns_empty_string_when_no_markdown(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FakeParsing:
        async def parse(self, **kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(markdown_full=None)

    class FakeClient:
        parsing = FakeParsing()

    class FakeLlamaCloud:
        def __init__(self, *, api_key: str) -> None:
            pass

        async def __aenter__(self) -> FakeClient:
            return FakeClient()

        async def __aexit__(self, *exc: object) -> bool:
            return False

    monkeypatch.setattr(llama_cloud, "AsyncLlamaCloud", FakeLlamaCloud)
    client = LlamaCloudExtractClient()
    with_key(client, "secret-key")

    assert await client.extract(Path("book.pdf")) == ""
