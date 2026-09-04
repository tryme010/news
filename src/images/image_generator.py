"""Generate a fallback AI editorial illustration when no licensed photo is
available. Internally always tagged as an AI-generated illustration, never
presented as a real photograph (spec #24).
"""
from __future__ import annotations

import logging
import os
from typing import Dict, Optional

logger = logging.getLogger("news_bot.images.generator")


def generate_editorial_image(topic_name: str, region: str = "") -> Optional[Dict]:
    provider = os.environ.get("IMAGE_GEN_PROVIDER", "").strip().lower()
    api_key = os.environ.get("IMAGE_GEN_API_KEY", "").strip()

    if not provider or not api_key:
        logger.info("No image generation provider configured; will use static fallback.")
        return None

    # Real integration point: call the configured provider (e.g. an
    # Anthropic/OpenAI-compatible image endpoint or a dedicated image API).
    # Left as a documented extension point since no image-gen credentials
    # are available in this environment; wire in the vendor SDK here.
    logger.info("Image generation provider '%s' configured but not implemented in this build.", provider)
    return None
