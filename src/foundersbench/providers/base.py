"""BYOK LLM provider abstraction.

Keys from environment: ANTHROPIC_API_KEY, OPENAI_API_KEY.
Recommended model: Claude Sonnet (citation discipline, persona, reasoning).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProviderResponse:
    text: str
    model: str
    # Token usage when reported by the provider
    input_tokens: int | None = None
    output_tokens: int | None = None


class LLMProvider(ABC):
    """Base interface: generate text from system prompt + user message."""

    name: str = "base"

    @abstractmethod
    async def generate(
        self,
        system_prompt: str,
        user_message: str,
        *,
        max_tokens: int = 2000,
        temperature: float = 0.7,
    ) -> ProviderResponse:
        """Generate a completion. Raises ProviderError on failure."""
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        """True if API key / credentials are available."""
        ...


class ProviderError(Exception):
    """Provider call failed (missing key, network, API error, etc.)."""
