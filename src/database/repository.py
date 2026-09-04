"""Repository layer: all SQLite access goes through here.

This isolates persistence so the strategy documented in migrations.py
(repository-backed SQLite file, committed by the GitHub Actions workflow)
can later be swapped for an external DB by changing only this file's
`get_connection`.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional

from src.database.migrations import migrate
from src.database.models import Article, Event, ImageAsset, RunStats, Source

DEFAULT_DB_PATH = "data/news.db"


class Repository:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._conn.row_factory = sqlite3.Row
        migrate(self._conn)

    def close(self) -> None:
        self._conn.close()

    @contextmanager
    def cursor(self) -> Iterator[sqlite3.Cursor]:
        cur = self._conn.cursor()
        try:
            yield cur
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            cur.close()

    # -------------------- sources --------------------
    def get_source_by_url(self, url: str) -> Optional[sqlite3.Row]:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM sources WHERE url = ?", (url,))
            return cur.fetchone()

    def upsert_source(self, source: Source) -> str:
        existing = self.get_source_by_url(source.url)
        if existing:
            return existing["id"]
        with self.cursor() as cur:
            cur.execute(
                """INSERT INTO sources (id, url, domain, title, published_at,
                   source_tier, credibility_score, fetched_at)
                   VALUES (?,?,?,?,?,?,?,?)""",
                (source.id, source.url, source.domain, source.title,
                 source.published_at, source.source_tier,
                 source.credibility_score, source.fetched_at),
            )
        return source.id

    # -------------------- events --------------------
    def find_event_by_fingerprint(self, fingerprint: str) -> Optional[sqlite3.Row]:
        with self.cursor() as cur:
            cur.execute("SELECT * FROM events WHERE fingerprint = ?", (fingerprint,))
            return cur.fetchone()

    def insert_event(self, event: Event) -> str:
        with self.cursor() as cur:
            cur.execute(
                """INSERT INTO events (id, fingerprint, topic_id, title, summary,
                   event_time, region, country, entities, verification_score,
                   status, is_sensitive, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (event.id, event.fingerprint, event.topic_id, event.title,
                 event.summary, event.event_time, event.region, event.country,
                 event.entities_json(), event.verification_score, event.status,
                 int(event.is_sensitive), event.created_at, event.updated_at),
            )
            for source_id in event.source_ids:
                cur.execute(
                    "INSERT OR IGNORE INTO event_sources (event_id, source_id) VALUES (?,?)",
                    (event.id, source_id),
                )
        return event.id

    def update_event_status(self, event_id: str, status: str, score: float) -> None:
        with self.cursor() as cur:
            cur.execute(
                "UPDATE events SET status = ?, verification_score = ? WHERE id = ?",
                (status, score, event_id),
            )

    # -------------------- articles (idempotency guard) --------------------
    def article_exists(self, event_id: str, website_id: str) -> bool:
        with self.cursor() as cur:
            cur.execute(
                "SELECT 1 FROM articles WHERE event_id = ? AND website_id = ?",
                (event_id, website_id),
            )
            return cur.fetchone() is not None

    def article_fingerprint_exists(self, fingerprint: str) -> bool:
        with self.cursor() as cur:
            cur.execute("SELECT 1 FROM articles WHERE fingerprint = ?", (fingerprint,))
            return cur.fetchone() is not None

    def insert_article(self, article: Article) -> str:
        with self.cursor() as cur:
            cur.execute(
                """INSERT OR IGNORE INTO articles
                   (id, event_id, website_id, title, slug, summary, body,
                    seo_title, meta_description, keywords, status,
                    quality_score, blogger_post_id, blogger_url, fingerprint,
                    created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (article.id, article.event_id, article.website_id, article.title,
                 article.slug, article.summary, article.body, article.seo_title,
                 article.meta_description, article.keywords_json(), article.status,
                 article.quality_score, article.blogger_post_id, article.blogger_url,
                 article.fingerprint, article.created_at),
            )
        return article.id

    def update_article_blogger_info(self, article_id: str, post_id: str, url: str, status: str) -> None:
        with self.cursor() as cur:
            cur.execute(
                "UPDATE articles SET blogger_post_id = ?, blogger_url = ?, status = ? WHERE id = ?",
                (post_id, url, status, article_id),
            )

    def recent_article_counts_by_website(self, days: int = 7) -> dict:
        with self.cursor() as cur:
            cur.execute(
                """SELECT website_id, COUNT(*) as cnt FROM articles
                   WHERE created_at >= datetime('now', ?)
                   GROUP BY website_id""",
                (f"-{days} days",),
            )
            return {row["website_id"]: row["cnt"] for row in cur.fetchall()}

    # -------------------- images --------------------
    def insert_image(self, image: ImageAsset) -> str:
        with self.cursor() as cur:
            cur.execute(
                """INSERT INTO images (id, article_id, image_url, source, license,
                   credit, retrieved_at) VALUES (?,?,?,?,?,?,?)""",
                (image.id, image.article_id, image.image_url, image.source,
                 image.license, image.credit, image.retrieved_at),
            )
        return image.id

    # -------------------- topics --------------------
    def touch_topic(self, topic_id: str, name: str) -> None:
        with self.cursor() as cur:
            cur.execute(
                """INSERT INTO topics (id, name, last_processed_at, recent_article_count, recent_event_count)
                   VALUES (?, ?, datetime('now'), 0, 0)
                   ON CONFLICT(id) DO UPDATE SET last_processed_at = datetime('now')""",
                (topic_id, name),
            )

    def get_topic_last_processed(self, topic_id: str) -> Optional[str]:
        with self.cursor() as cur:
            cur.execute("SELECT last_processed_at FROM topics WHERE id = ?", (topic_id,))
            row = cur.fetchone()
            return row["last_processed_at"] if row else None

    # -------------------- runs / errors --------------------
    def insert_run(self, run: RunStats) -> None:
        with self.cursor() as cur:
            cur.execute(
                """INSERT INTO runs (id, started_at, finished_at, topics_processed,
                   candidates_found, events_verified, duplicates_removed,
                   articles_generated, drafts_created, errors, dry_run, demo_mode)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (run.id, run.started_at, run.finished_at, run.topics_processed,
                 run.candidates_found, run.events_verified, run.duplicates_removed,
                 run.articles_generated, run.drafts_created, run.errors,
                 int(run.dry_run), int(run.demo_mode)),
            )

    def finalize_run(self, run: RunStats) -> None:
        with self.cursor() as cur:
            cur.execute(
                """UPDATE runs SET finished_at=?, topics_processed=?, candidates_found=?,
                   events_verified=?, duplicates_removed=?, articles_generated=?,
                   drafts_created=?, errors=? WHERE id=?""",
                (run.finished_at, run.topics_processed, run.candidates_found,
                 run.events_verified, run.duplicates_removed, run.articles_generated,
                 run.drafts_created, run.errors, run.id),
            )

    def log_error(self, run_id: str, component: str, message: str) -> None:
        import uuid
        from src.utils.time import utcnow_iso
        with self.cursor() as cur:
            cur.execute(
                "INSERT INTO errors (id, run_id, component, message, created_at) VALUES (?,?,?,?,?)",
                (f"err_{uuid.uuid4().hex[:12]}", run_id, component, message, utcnow_iso()),
            )
