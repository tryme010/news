"""Lightweight dataclass models mirroring the SQLite schema.

These are plain data containers (not an ORM) to keep the system simple and
dependency-light, as requested by the spec (SQLite MVP, repository pattern).
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import List, Optional

from src.utils.time import utcnow_iso


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class Source:
    url: str
    domain: str
    title: str
    published_at: Optional[str] = None
    source_tier: int = 4
    credibility_score: float = 0.4
    id: str = field(default_factory=lambda: new_id("src"))
    fetched_at: str = field(default_factory=utcnow_iso)


@dataclass
class Event:
    topic_id: str
    title: str
    summary: str
    fingerprint: str
    event_time: Optional[str] = None
    region: str = "Global"
    country: str = ""
    entities: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)
    verification_score: float = 0.0
    status: str = "candidate"  # candidate|reject|weak|review|good|strong
    is_sensitive: bool = False
    id: str = field(default_factory=lambda: new_id("evt"))
    created_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)

    def entities_json(self) -> str:
        return json.dumps(self.entities, ensure_ascii=False)


@dataclass
class Article:
    event_id: str
    website_id: str
    title: str
    slug: str
    summary: str
    body: str
    seo_title: str = ""
    meta_description: str = ""
    keywords: List[str] = field(default_factory=list)
    status: str = "draft_ready"  # draft_ready|below_quality|blogger_created|failed
    quality_score: float = 0.0
    blogger_post_id: Optional[str] = None
    blogger_url: Optional[str] = None
    fingerprint: str = ""
    id: str = field(default_factory=lambda: new_id("art"))
    created_at: str = field(default_factory=utcnow_iso)

    def keywords_json(self) -> str:
        return json.dumps(self.keywords, ensure_ascii=False)


@dataclass
class ImageAsset:
    article_id: str
    image_url: str
    source: str
    license: str
    credit: str
    id: str = field(default_factory=lambda: new_id("img"))
    retrieved_at: str = field(default_factory=utcnow_iso)


@dataclass
class RunStats:
    id: str = field(default_factory=lambda: new_id("run"))
    started_at: str = field(default_factory=utcnow_iso)
    finished_at: Optional[str] = None
    topics_processed: int = 0
    candidates_found: int = 0
    events_verified: int = 0
    duplicates_removed: int = 0
    articles_generated: int = 0
    drafts_created: int = 0
    errors: int = 0
    dry_run: bool = False
    demo_mode: bool = False
