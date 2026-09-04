"""Real OpenAI provider.

Requires OPENAI_API_KEY (mapped from AI_API_KEY) and the `openai` package.
"""
from __future__ import annotations

import os
from typing import Optional

from src.ai.base import AIProvider
from src.utils.retry import retry_with_backoff


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        api_key = api_key or os.environ.get("AI_API_KEY") or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OpenAIProvider requires an API key. Set AI_API_KEY (or OPENAI_API_KEY) "
                "in your environment / GitHub Secrets."
            )
        try:
            import openai  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "The 'openai' package is required for OpenAIProvider. "
                "Install it via requirements.txt."
            ) from exc

        import openai
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def generate(self, prompt: str, *, system: Optional[str] = None,
                 max_tokens: int = 2000, temperature: float = 0.4) -> str:
        def _call():
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""

        return retry_with_backoff(_call)
