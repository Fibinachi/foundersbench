"""OpenAI provider (GPT).

BYOK: OPENAI_API_KEY environment variable.
"""

from __future__ import annotations

import os

from foundersbench.providers.base import (
    LLMProvider,
    ProviderError,
    ProviderResponse,
)

DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL):
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
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
            raise ProviderError("OPENAI_API_KEY not set")
        try:
            import openai
        except ImportError as e:
            raise ProviderError("openai package not installed") from e

        client = openai.AsyncOpenAI(api_key=self.api_key)
        try:
            resp = await client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
            )
        except Exception as e:
            raise ProviderError(f"OpenAI API error: {e}") from e

        choice = resp.choices[0]
        text = choice.message.content or ""
        usage = getattr(resp, "usage", None)
        return ProviderResponse(
            text=text,
            model=self.model,
            input_tokens=getattr(usage, "prompt_tokens", None),
            output_tokens=getattr(usage, "completion_tokens", None),
        )
