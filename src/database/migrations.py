"""SQLite schema creation / migration.

Persistence strategy (see README section 'Persistence on GitHub Actions'):
GitHub Actions runners are ephemeral, so data/news.db is restored from and
committed back to the repository itself at the start/end of each workflow
run (a lightweight 'repository-backed database' strategy). This avoids
provisioning an external database for the MVP while still giving the
pipeline durable history across runs. See GITHUB_SETUP.md for details and
for how to swap in an external Postgres/Turso/Supabase DB later without
changing application code (only `repository.py`'s connection needs to change).
"""
from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS topics (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    last_processed_at TEXT,
    recent_article_count INTEGER DEFAULT 0,
    recent_event_count INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    topics_processed INTEGER DEFAULT 0,
    candidates_found INTEGER DEFAULT 0,
    events_verified INTEGER DEFAULT 0,
    duplicates_removed INTEGER DEFAULT 0,
    articles_generated INTEGER DEFAULT 0,
    drafts_created INTEGER DEFAULT 0,
    errors INTEGER DEFAULT 0,
    dry_run INTEGER DEFAULT 0,
    demo_mode INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    domain TEXT,
    title TEXT,
    published_at TEXT,
    source_tier INTEGER,
    credibility_score REAL,
    fetched_at TEXT
);

CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    fingerprint TEXT NOT NULL,
    topic_id TEXT,
    title TEXT,
    summary TEXT,
    event_time TEXT,
    region TEXT,
    country TEXT,
    entities TEXT,
    verification_score REAL,
    status TEXT,
    is_sensitive INTEGER DEFAULT 0,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS event_sources (
    event_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    PRIMARY KEY (event_id, source_id)
);

CREATE TABLE IF NOT EXISTS websites (
    id TEXT PRIMARY KEY,
    name TEXT,
    blogger_blog_id TEXT
);

CREATE TABLE IF NOT EXISTS articles (
    id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    website_id TEXT NOT NULL,
    title TEXT,
    slug TEXT,
    summary TEXT,
    body TEXT,
    seo_title TEXT,
    meta_description TEXT,
    keywords TEXT,
    status TEXT,
    quality_score REAL,
    blogger_post_id TEXT,
    blogger_url TEXT,
    fingerprint TEXT,
    created_at TEXT,
    UNIQUE (event_id, website_id)
);

CREATE TABLE IF NOT EXISTS article_sources (
    article_id TEXT NOT NULL,
    source_id TEXT NOT NULL,
    PRIMARY KEY (article_id, source_id)
);

CREATE TABLE IF NOT EXISTS images (
    id TEXT PRIMARY KEY,
    article_id TEXT,
    image_url TEXT,
    source TEXT,
    license TEXT,
    credit TEXT,
    retrieved_at TEXT
);

CREATE TABLE IF NOT EXISTS errors (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    component TEXT,
    message TEXT,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_fingerprint ON events (fingerprint);
CREATE INDEX IF NOT EXISTS idx_articles_event ON articles (event_id);
CREATE INDEX IF NOT EXISTS idx_articles_website ON articles (website_id);
CREATE INDEX IF NOT EXISTS idx_sources_url ON sources (url);
"""


def migrate(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    conn.commit()
