from typing import final

from services.common.schema import Schema


@final
class TTSResult(Schema):
    """Synthesized audio bytes plus the provider request id, if any."""

    audio: bytes
    request_id: str | None = None
