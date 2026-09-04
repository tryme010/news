"""High-level draft creation flow: builds HTML content from an Article
model, checks idempotency, and calls BloggerClient.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from src.blogger.client import BloggerClient
from src.database.models import Article, ImageAsset
from src.database.repository import Repository

logger = logging.getLogger("news_bot.blogger.drafts")


def build_html(article: Article, image: Optional[ImageAsset], sources_html: str = "") -> str:
    parts = []
    if image:
        parts.append(
            f'<p><img src="{image.image_url}" alt="{article.title}" '
            f'style="max-width:100%;height:auto;"/></p>'
            f'<p><small>{image.credit} ({image.source})</small></p>'
        )
    parts.append(f"<p><em>{article.summary}</em></p>")
    for para in article.body.split("\n\n"):
        para = para.strip()
        if para:
            parts.append(f"<p>{para}</p>")
    if sources_html:
        parts.append(f"<p><small>{sources_html}</small></p>")
    return "\n".join(parts)


def create_draft_for_article(
    article: Article,
    website: Dict,
    repo: Repository,
    blogger_client: BloggerClient,
    image: Optional[ImageAsset] = None,
    sources_html: str = "",
) -> bool:
    """Returns True if a draft was created (or already existed / dry-run)."""
    if repo.article_exists(article.event_id, article.website_id) and article.blogger_post_id:
        logger.info("Article already has a Blogger draft; skipping (idempotency).")
        return True

    blog_id = website.get("blogger_blog_id", "")
    if not blog_id:
        logger.warning("Website %s has no blogger_blog_id configured; skipping draft creation.", website.get("id"))
        return False

    html = build_html(article, image, sources_html)
    result = blogger_client.create_draft(blog_id, article.title, html)
    if not result:
        return False

    post_id = result.get("id", "")
    url = result.get("url", "")
    repo.update_article_blogger_info(article.id, post_id, url, "blogger_created")
    return True
