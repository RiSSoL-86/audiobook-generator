from typing import final, override

import httpx

from services.tts.clients.base import TTSClient
from services.tts.schemas import TTSResult


@final
class SonioxTTSClient(TTSClient):
    """Soniox TTS over HTTP."""

    ENDPOINT = "https://tts-rt.soniox.com/tts"

    @override
    async def synthesize(self, text: str) -> TTSResult:
        """Post one block to Soniox and return its audio bytes."""
        key = self.settings.tts.soniox_api_key
        if key is None:
            msg = "SONIOX_API_KEY is required for the tts stage"
            raise ValueError(msg)
        async with httpx.AsyncClient() as http:
            response = await http.post(
                url=self.ENDPOINT,
                headers={"Authorization": f"Bearer {key.get_secret_value()}"},
                json={
                    "model": self.settings.tts.model,
                    "voice": self.settings.tts.voice,
                    "language": self.settings.tts.language,
                    "speed": self.settings.tts.speed,
                    "audio_format": self.settings.tts.audio_format,
                    "text": text,
                },
                timeout=self.settings.tts.request_timeout,
            )
        response.raise_for_status()
        return TTSResult(
            audio=response.content,
            request_id=response.headers.get("x-request-id"),
        )
