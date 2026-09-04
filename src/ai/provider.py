"""Factory that returns the configured AIProvider implementation."""
from __future__ import annotations

import os

from src.ai.base import AIProvider


def get_ai_provider() -> AIProvider:
    provider_name = os.environ.get("AI_PROVIDER", "mock").strip().lower()

    if provider_name == "mock":
        from src.ai.mock_provider import MockProvider
        return MockProvider()
    if provider_name == "anthropic":
        from src.ai.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    if provider_name == "openai":
        from src.ai.openai_provider import OpenAIProvider
        return OpenAIProvider()

    raise ValueError(
        f"Unknown AI_PROVIDER '{provider_name}'. Expected one of: mock, anthropic, openai."
    )
