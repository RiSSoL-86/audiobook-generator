from typing import final

from services.common.schema import Schema


@final
class TranslateResult(Schema):
    """Translated markdown text plus the provider request id, if any."""

    text: str
    request_id: str | None = None
