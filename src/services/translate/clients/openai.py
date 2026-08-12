from typing import final, override

import httpx
from openai import AsyncOpenAI

from services.translate.clients.base import TranslateClient
from services.translate.schemas import TranslateResult


@final
class OpenAITranslateClient(TranslateClient):
    """Literary translation via the OpenAI Chat Completions API."""

    PROMPT = (
        "You are a professional literary translator. Translate the user's "
        "Markdown from {source} to {target}. The input is one fragment of a "
        "larger chapter, so translate exactly what is given without adding an "
        "introduction, conclusion, or bridging text.\n"
        "Preserve the Markdown structure exactly and never change the type of "
        "any line: a heading stays a heading with the same number of leading "
        "'#' characters, a list item stays a list item with the same marker, "
        "a blockquote stays a blockquote, and body text stays body text. Keep "
        "emphasis markers, links, inline code, and blank lines as they are. "
        "Translate the visible text of every heading, list item, and sentence "
        "-- do not romanize or leave it in the source language. Do not add, "
        "remove, reorder, summarize, or comment on anything, and do not wrap "
        "the result in a code fence. Output only the translated Markdown."
    )

    @override
    async def translate(
        self, text: str, source_lang: str, target_lang: str
    ) -> TranslateResult:
        """Send one markdown block to OpenAI and return its translation."""
        key = self.settings.translate.openai_api_key
        if key is None:
            msg = (
                "TRANSLATE_OPENAI_API_KEY is required for the translate stage"
            )
            raise ValueError(msg)
        prompt = self.PROMPT.format(source=source_lang, target=target_lang)
        http_client = httpx.AsyncClient(trust_env=True)
        try:
            async with AsyncOpenAI(
                api_key=key.get_secret_value(),
                timeout=self.settings.translate.request_timeout,
                http_client=http_client,
            ) as client:
                response = await client.chat.completions.create(
                    model=self.settings.translate.model,
                    messages=[
                        {"role": "system", "content": prompt},
                        {"role": "user", "content": text},
                    ],
                )
        finally:
            if http_client is not None:
                await http_client.aclose()
        content = response.choices[0].message.content
        if not content:
            msg = "OpenAI returned an empty translation"
            raise RuntimeError(msg)
        if content.strip() == text.strip():
            msg = "OpenAI echoed the source untranslated"
            raise RuntimeError(msg)
        return TranslateResult(text=content, request_id=response.id)
