from src.writer.seo import slugify_fallback


def test_slugify_basic():
    assert slugify_fallback("Hello World News") == "hello-world-news"


def test_slugify_strips_special_chars():
    slug = slugify_fallback("Breaking: Company X raises $50M!!")
    assert " " not in slug
    assert "!" not in slug
    assert ":" not in slug


def test_slugify_deterministic():
    a = slugify_fallback("Same Title Twice")
    b = slugify_fallback("Same Title Twice")
    assert a == b
