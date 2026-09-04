"""Normalize image metadata into the ImageAsset persistence shape."""
from __future__ import annotations

from typing import Dict, Optional

from src.database.models import ImageAsset


def to_image_asset(article_id: str, image_dict: Optional[Dict]) -> Optional[ImageAsset]:
    if not image_dict:
        return None
    return ImageAsset(
        article_id=article_id,
        image_url=image_dict.get("image_url", ""),
        source=image_dict.get("source", ""),
        license=image_dict.get("license", ""),
        credit=image_dict.get("credit", ""),
    )
