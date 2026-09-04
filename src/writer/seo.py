"""SEO metadata generation + deterministic slug fallback."""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from typing import Dict

from src.ai.base import AIProvider

logger = logging.getLogger("news_bot.writer.seo")


def slugify_fallback(text: str, max_len: int = 60) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE).strip().lower()
    text = re.sub(r"[\s_]+", "-", text)
    return text[:max_len].strip("-") or "news"


def _load_prompt_template() -> str:
    with open("config/prompts/headline.txt", "r", encoding="utf-8") as f:
        return f.read()


def generate_seo(article_body: str, headline: str, website_focus: str, ai: AIProvider) -> Dict:
    template = _load_prompt_template()
    prompt = (
        f"{template}\n\nHEADLINE: {headline}\nWEBSITE FOCUS: {website_focus}\n"
        f"ARTICLE BODY:\n{article_body[:3000]}"
    )
    try:
        result = ai.generate_json(prompt, max_tokens=500, temperature=0.2)
    except Exception as exc:  # noqa: BLE001
        logger.warning("SEO generation failed, using fallback: %s", exc)
        result = {}

    slug = result.get("slug") or slugify_fallback(headline)
    return {
        "seo_title": result.get("seo_title", headline)[:70],
        "meta_description": result.get("meta_description", "")[:160],
        "slug": slugify_fallback(slug),
        "keywords": result.get("keywords", []),
    }
