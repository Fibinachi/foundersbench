"""Provider package."""

from foundersbench.providers.anthropic_provider import AnthropicProvider
from foundersbench.providers.base import LLMProvider, ProviderError, ProviderResponse
from foundersbench.providers.openai_provider import OpenAIProvider

__all__ = [
    "AnthropicProvider",
    "LLMProvider",
    "OpenAIProvider",
    "ProviderError",
    "ProviderResponse",
]


def default_provider() -> LLMProvider:
    """First configured provider, preferring Anthropic (recommended)."""
    for cls in (AnthropicProvider, OpenAIProvider):
        p = cls()
        if p.is_configured():
            return p
    # Return Anthropic unconfigured; calls will raise ProviderError with
    # a clear message, which the agent service labels as fallback.
    return AnthropicProvider()
