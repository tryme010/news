"""Pick the best available image for an article: licensed photo -> AI
illustration -> static category fallback -> no image (never fails the
article pipeline, per spec #25).
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from src.images.image_generator import generate_editorial_image
from src.images.image_search import search_licensed_image
from src.images.license import is_license_approved

logger = logging.getLogger("news_bot.images.selector")

# Static, always-available fallback illustrations by broad category.
STATIC_FALLBACKS = {
    "technology": "https://images.unsplash.com/photo-1518770660439-4636190af475",
    "business": "https://images.unsplash.com/photo-1454165804606-c3d57bc86b40",
    "sports": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211",
    "health": "https://images.unsplash.com/photo-1505751172876-fa1923c5c528",
    "culture": "https://images.unsplash.com/photo-1513364776144-60967b0f800f",
    "education": "https://images.unsplash.com/photo-1523050854058-8df90110c9f1",
    "general": "https://images.unsplash.com/photo-1495020689067-958852a7765e",
}


def select_image(query: str, category: str = "general", region: str = "",
                  allow_ai_generated: bool = True, allow_missing: bool = True) -> Optional[Dict]:
    licensed = search_licensed_image(query)
    if licensed and is_license_approved(licensed.get("license", "")):
        return licensed

    if allow_ai_generated:
        generated = generate_editorial_image(query, region)
        if generated and is_license_approved(generated.get("license", "ai_generated")):
            return generated

    fallback_url = STATIC_FALLBACKS.get(category, STATIC_FALLBACKS["general"])
    if fallback_url:
        return {
            "image_url": fallback_url,
            "source": "static_fallback",
            "license": "editorial_use",
            "credit": "Editorial stock fallback",
        }

    if allow_missing:
        logger.info("No image available for query '%s'; proceeding without image.", query)
        return None

    return None
