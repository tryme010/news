"""Generate the original Arabic article body for one (event, website) pair.

Implements spec sections 16-19: distinct editorial angle per website,
original prose, length constraints, no fabrication.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List

from src.ai.base import AIProvider

logger = logging.getLogger("news_bot.writer.article_generator")


def _load_prompt_template() -> str:
    with open("config/prompts/article.txt", "r", encoding="utf-8") as f:
        return f.read()


def generate_article(event: Dict, website: Dict, sources: List[Dict], ai: AIProvider,
                      min_words: int = 500, max_words: int = 900) -> Dict:
    template = (
        _load_prompt_template()
        .replace("{min_words}", str(min_words))
        .replace("{max_words}", str(max_words))
    )

    sources_payload = [
        {"title": s.get("title"), "summary": s.get("summary", "")[:600], "url": s.get("url")}
        for s in sources
    ]
    payload = {
        "event_title": event.get("title"),
        "event_summary": event.get("summary"),
        "region": event.get("region"),
        "country": event.get("country"),
        "entities": event.get("entities", []),
        "is_sensitive": event.get("is_sensitive", False),
        "website_name": website.get("name"),
        "website_editorial_focus": website.get("editorial_focus", []),
        "sources": sources_payload,
    }

    prompt = f"{template}\n\nEVENT + WEBSITE DATA:\n{json.dumps(payload, ensure_ascii=False)}"

    result = ai.generate_json(prompt, max_tokens=5000, temperature=0.4)

    body = result.get("body", "")
    word_count = len(body.split())

    return {
        "headline": result.get("headline", event.get("title", "")),
        "summary": result.get("summary", ""),
        "body": body,
        "entities": result.get("entities", event.get("entities", [])),
        "editorial_angle": result.get("editorial_angle", ""),
        "word_count": word_count,
    }
