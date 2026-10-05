"""Anthropic provider (Claude). Recommended default.

BYOK: ANTHROPIC_API_KEY environment variable.
Recommended model: claude-sonnet-4-5 (citation discipline, persona without
caricature, analogical reasoning for brief-and-ask mode).
"""

from __future__ import annotations

import os

from foundersbench.providers.base import (
    LLMProvider,
    ProviderError,
    ProviderResponse,
)

DEFAULT_MODEL = "claude-sonnet-4-5"


class AnthropicProvider(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        self.model = model

    def is_configured(self) -> bool:
        return bool(self.api_key)

    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> ProviderResponse:
        if not self.is_configured():
            raise ProviderError("ANTHROPIC_API_KEY not set")
        try:
            import anthropic
        except ImportError as e:
            raise ProviderError("anthropic package not installed") from e

        client = anthropic.AsyncAnthropic(api_key=self.api_key)
        try:
            msg = await client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_message}],
            )
        except Exception as e:
            raise ProviderError(f"Anthropic API error: {e}") from e

        text = "".join(
            b.text for b in msg.content if getattr(b, "type", "") == "text"
        )
        usage = getattr(msg, "usage", None)
        return ProviderResponse(
            text=text,
            model=self.model,
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
        )
