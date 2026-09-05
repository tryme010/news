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

        selected_model = model or os.environ.get(
            "GEMINI_MODEL",
            "gemini-3.6-flash",
        )

        fallback_models = os.environ.get(
            "GEMINI_FALLBACK_MODELS",
            "gemini-3.6-flash,gemini-3.5-flash,gemini-3.1-flash-lite",
        ).split(",")

        self._models = []
        for candidate in [selected_model, *fallback_models]:
            candidate = candidate.strip()
            if candidate and candidate not in self._models:
                self._models.append(candidate)

    def _generate_with_model(
        self,
        model: str,
        prompt: str,
        *,
        system: Optional[str],
        max_tokens: int,
        temperature: float,
    ) -> str:
        url = (
            "https://generativelanguage.googleapis.com/"
            f"v1beta/models/{model}:generateContent"
        )

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max(max_tokens, 2000),
            },
        }

        if "json" in prompt.lower():
            payload["generationConfig"]["responseMimeType"] = (
                "application/json"
            )

        if system:
            payload["systemInstruction"] = {
                "parts": [{"text": system}],
            }

        response = requests.post(
            url,
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
                f"Gemini returned no candidates for {model}: {data}"
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
            finish_reason = candidates[0].get("finishReason", "")
            raise RuntimeError(
                f"Gemini returned an empty response for {model}. "
                f"finishReason={finish_reason}: {data}"
            )

        return text

    def generate(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        max_tokens: int = 2000,
        temperature: float = 0.4,
    ) -> str:
        last_error: Optional[Exception] = None

        for model in self._models:
            try:
                return retry_with_backoff(
                    lambda: self._generate_with_model(
                        model,
                        prompt,
                        system=system,
                        max_tokens=max_tokens,
                        temperature=temperature,
                    )
                )
            except requests.HTTPError as exc:
                last_error = exc

                status = (
                    exc.response.status_code
                    if exc.response is not None
                    else None
                )

                if status in (429, 500, 502, 503, 504):
                    continue

                raise
            except RuntimeError as exc:
                last_error = exc
                continue

        raise RuntimeError(
            "All configured Gemini models failed. "
            f"Models tried: {', '.join(self._models)}. "
            f"Last error: {last_error}"
        )