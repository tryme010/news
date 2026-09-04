"""Real Anthropic (Claude) provider.

Requires ANTHROPIC_API_KEY (mapped from AI_API_KEY in settings) and the
`anthropic` package (see requirements.txt).
"""
from __future__ import annotations

import os
from typing import Optional

from src.ai.base import AIProvider
from src.utils.retry import retry_with_backoff


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: Optional[str] = None, model: str = "claude-sonnet-4-6"):
        api_key = api_key or os.environ.get("AI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "AnthropicProvider requires an API key. Set AI_API_KEY (or ANTHROPIC_API_KEY) "
                "in your environment / GitHub Secrets."
            )
        try:
            import anthropic  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "The 'anthropic' package is required for AnthropicProvider. "
                "Install it via requirements.txt."
            ) from exc

        import anthropic
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate(self, prompt: str, *, system: Optional[str] = None,
                 max_tokens: int = 2000, temperature: float = 0.4) -> str:
        def _call():
            kwargs = {
                "model": self._model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                kwargs["system"] = system
            resp = self._client.messages.create(**kwargs)
            parts = [block.text for block in resp.content if getattr(block, "type", None) == "text"]
            return "".join(parts)

        return retry_with_backoff(_call)
