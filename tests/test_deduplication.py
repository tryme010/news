from src.deduplication.fingerprint import build_fingerprint
from src.deduplication.normalizer import normalize_title, normalize_url
from src.deduplication.similarity import group_candidates_into_events, title_similarity


def test_normalize_url_strips_tracking_and_www():
    a = normalize_url("https://www.Example.com/Article/?utm_source=x&id=1")
    b = normalize_url("https://example.com/Article?id=1")
    assert a == b


def test_normalize_title_arabic_variants():
    a = normalize_title("الشّركة تُعلن إطلاق المنتج")
    b = normalize_title("الشركة تعلن اطلاق المنتج")
    assert a == b


def test_fingerprint_same_event_same_fingerprint():
    # Same entities/title/location, close in time (same 24h bucket) -> identical fingerprint.
    # (Near-identical-but-not-exact titles are handled by title_similarity grouping instead,
    # see test_group_candidates_merges_duplicates.)
    fp1 = build_fingerprint("Apple launches new iPhone model", ["Apple"], "United States", "2026-09-04T10:00:00")
    fp2 = build_fingerprint("Apple launches new iPhone model", ["Apple"], "United States", "2026-09-04T11:00:00")
    assert fp1 == fp2


def test_fingerprint_different_events_differ():
    fp1 = build_fingerprint("Apple launches new iPhone model", ["Apple"], "United States")
    fp2 = build_fingerprint("Government announces new tax policy", ["Ministry of Finance"], "Egypt")
    assert fp1 != fp2


def test_group_candidates_merges_duplicates():
    candidates = [
        {"title": "شركة تعلن عن نتائج قياسية", "url": "https://a.com/1", "published_at": None},
        {"title": "شركة تعلن عن نتائج قياسية", "url": "https://b.com/1", "published_at": None},
        {"title": "فريق كرة القدم يفوز بالبطولة", "url": "https://c.com/1", "published_at": None},
    ]
    groups = group_candidates_into_events(candidates)
    assert len(groups) == 2


def test_title_similarity_high_for_near_duplicates():
    sim = title_similarity("شركة تطلق منتجاً جديداً اليوم", "شركة تطلق منتجا جديدا اليوم")
    assert sim > 0.8
