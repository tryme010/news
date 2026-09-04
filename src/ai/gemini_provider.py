"""Google Gemini AI provider using the Gemini REST API."""
from __future__ import annotations

import os
from typing import Optional

import requests

from src.ai.base import AIProvider
from src.utils.retry import retry_with_backoff


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self._api_key = (
            api_key
            or os.environ.get("GEMINI_API_KEY")
            or os.environ.get("GOOGLE_API_KEY")
        )

        if not self._api_key:
            raise RuntimeError(
                "GeminiProvider requires an API key. "
                "Set GEMINI_API_KEY in your environment / GitHub Secrets."
            )

        self._model = model or os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")
        self._url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{self._model}:generateContent"
        )

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.4,
    ) -> str:

        def _call() -> str:
            contents = []

            if system:
                contents.append(
                    {
                        "role": "user",
                        "parts": [{"text": system}],
                    }
                )

            contents.append(
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            )

            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            }

            response = requests.post(
                self._url,
                headers={
                    "x-goog-api-key": self._api_key,
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=90,
            )

            response.raise_for_status()
            data = response.json()

            candidates = data.get("candidates") or []
            if not candidates:
                raise RuntimeError(
                    f"Gemini returned no candidates: {data}"
                )

            parts = (
                candidates[0]
                .get("content", {})
                .get("parts", [])
            )

            text = "".join(
                part.get("text", "")
                for part in parts
                if isinstance(part, dict)
            ).strip()

            if not text:
                raise RuntimeError(
                    f"Gemini returned an empty response: {data}"
                )

            return text

        return retry_with_backoff(_call)