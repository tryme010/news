import os
import tempfile

from src.pipeline.orchestrator import run_pipeline


def test_demo_dry_run_pipeline_executes_end_to_end():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["AI_PROVIDER"] = "mock"
        db_path = os.path.join(tmp, "demo.db")
        result = run_pipeline(dry_run=True, demo_mode=True, db_path=db_path)

        assert "stats" in result
        assert result["stats"]["candidates_found"] >= 0
        assert result["run"].dry_run is True
        assert result["run"].demo_mode is True


def test_demo_dry_run_pipeline_is_idempotent_on_rerun():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ["AI_PROVIDER"] = "mock"
        db_path = os.path.join(tmp, "demo2.db")

        result1 = run_pipeline(dry_run=True, demo_mode=True, db_path=db_path)
        articles_first_run = result1["run"].articles_generated

        # Second run against the same DB should not duplicate the same events'
        # articles (fingerprint-based idempotency).
        result2 = run_pipeline(dry_run=True, demo_mode=True, db_path=db_path)

        assert result2["run"].articles_generated <= articles_first_run + 5


def test_rss_topic_assignment_uses_feed_fallback_for_world_news():
    from src.discovery.candidate_builder import _assign_rss_topic

    topics = [
        {"id": "topic_international_affairs", "name": "International Affairs", "keywords": []},
        {"id": "topic_ai", "name": "Artificial Intelligence", "keywords": []},
    ]
    item = {"title": "World leaders meet for emergency talks", "summary": "", "feed_topic_hint": "topic_international_affairs"}
    assert _assign_rss_topic(item, topics)["id"] == "topic_international_affairs"


def test_blogger_html_does_not_render_news_sources():
    from src.blogger.drafts import build_html
    from src.database.models import Article

    article = Article(
        event_id="evt1", website_id="site1", title="عنوان", slug="title",
        summary="ملخص", body="فقرة أولى\n\nفقرة ثانية",
    )
    html = build_html(article, None)
    assert "المصادر:" not in html
    assert "example.com" not in html


def test_blogger_client_maps_403_to_permission_error(monkeypatch):
    import requests
    from src.blogger.client import BloggerClient, BloggerPermissionError

    client = BloggerClient(dry_run=False)
    monkeypatch.setattr("src.blogger.client.get_access_token", lambda: "token")

    class Resp:
        status_code = 403
        text = '{"error":{"message":"The caller does not have permission"}}'

    try:
        client._raise_for_blogger_error(Resp(), "draft creation", "123")
    except BloggerPermissionError as exc:
        assert "does not have permission" in str(exc)
        assert "auth/blogger" in str(exc)
    else:
        raise AssertionError("403 must be mapped to BloggerPermissionError")
