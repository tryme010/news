"""Abstract interface every AI provider must implement.

The rest of the application only ever talks to this interface, never to a
specific vendor SDK. This keeps the system provider-agnostic (see
config AI_PROVIDER=openai|anthropic|mock).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class AIProvider(ABC):
    """Common contract for all AI providers used by the pipeline."""

    name: str = "base"

    @abstractmethod
    def generate(self, prompt: str, *, system: Optional[str] = None,
                 max_tokens: int = 2000, temperature: float = 0.4) -> str:
        """Return raw text completion for a prompt."""
        raise NotImplementedError

    def generate_json(self, prompt: str, *, system: Optional[str] = None,
                       max_tokens: int = 2000, temperature: float = 0.3) -> Dict[str, Any]:
        """Return a parsed JSON object. Providers may override for native
        JSON-mode support; default implementation strips code fences and
        parses the raw text.
        """
        import json
        import re

        raw = self.generate(prompt, system=system, max_tokens=max_tokens,
                             temperature=temperature)
        cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            # Try to salvage the largest {...} block in the response.
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if match:
                return json.loads(match.group(0))
            raise ValueError(f"AI provider '{self.name}' did not return valid JSON: {exc}\nRaw: {raw[:500]}")

    def classify(self, text: str, categories: list, *, system: Optional[str] = None) -> str:
        """Default classify implementation built on top of generate()."""
        prompt = (
            f"Classify the following text into exactly one of these categories: "
            f"{', '.join(categories)}.\n\nText:\n{text}\n\n"
            f"Respond with only the category name, nothing else."
        )
        result = self.generate(prompt, system=system, max_tokens=20, temperature=0)
        return result.strip()

    def verify(self, prompt: str, *, system: Optional[str] = None) -> Dict[str, Any]:
        return self.generate_json(prompt, system=system, max_tokens=800, temperature=0.1)

    def summarize(self, text: str, *, max_words: int = 80, system: Optional[str] = None) -> str:
        prompt = f"Summarize the following text in at most {max_words} words:\n\n{text}"
        return self.generate(prompt, system=system, max_tokens=300, temperature=0.3)
