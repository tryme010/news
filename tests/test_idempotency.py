import os
import tempfile

from src.database.models import Article, Event, Source
from src.database.repository import Repository


def test_article_exists_prevents_duplicate_insert():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test.db")
        repo = Repository(db_path)

        event = Event(topic_id="t1", title="Test event", summary="s", fingerprint="fp1")
        repo.insert_event(event)

        article1 = Article(event_id=event.id, website_id="site_01", title="T", slug="t",
                            summary="s", body="b", fingerprint="fp1:site_01")
        repo.insert_article(article1)

        assert repo.article_exists(event.id, "site_01") is True

        # Re-running the same insert (simulating a rerun after a crash) must not error.
        article2 = Article(event_id=event.id, website_id="site_01", title="T2", slug="t2",
                            summary="s2", body="b2", fingerprint="fp1:site_01")
        repo.insert_article(article2)  # INSERT OR IGNORE due to UNIQUE(event_id, website_id)

        with repo.cursor() as cur:
            cur.execute("SELECT COUNT(*) as c FROM articles WHERE event_id=? AND website_id=?",
                        (event.id, "site_01"))
            count = cur.fetchone()["c"]
        assert count == 1
        repo.close()


def test_event_fingerprint_lookup_prevents_duplicate_events():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test2.db")
        repo = Repository(db_path)

        event = Event(topic_id="t1", title="Test event", summary="s", fingerprint="fp-unique")
        repo.insert_event(event)

        found = repo.find_event_by_fingerprint("fp-unique")
        assert found is not None
        assert found["id"] == event.id
        repo.close()


def test_source_upsert_is_idempotent():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = os.path.join(tmp, "test3.db")
        repo = Repository(db_path)

        src = Source(url="https://example.com/a", domain="example.com", title="A")
        id1 = repo.upsert_source(src)

        src2 = Source(url="https://example.com/a", domain="example.com", title="A again")
        id2 = repo.upsert_source(src2)

        assert id1 == id2
        repo.close()
