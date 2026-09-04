"""URL and title normalization utilities used across discovery/dedup."""
from __future__ import annotations

import re
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

TRACKING_PARAMS = {
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content",
    "fbclid", "gclid", "ref", "ref_src", "cmp", "spm",
}


def normalize_url(url: str) -> str:
    if not url:
        return url
    parsed = urlparse(url.strip())
    query_pairs = [(k, v) for k, v in parse_qsl(parsed.query) if k.lower() not in TRACKING_PARAMS]
    query_pairs.sort()
    normalized_query = urlencode(query_pairs)
    path = parsed.path.rstrip("/") or "/"
    netloc = parsed.netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    normalized = urlunparse((parsed.scheme.lower() or "https", netloc, path, "", normalized_query, ""))
    return normalized


_ARABIC_DIACRITICS = re.compile(r"[\u0617-\u061A\u064B-\u0652]")


def normalize_title(title: str) -> str:
    if not title:
        return ""
    text = title.strip()
    text = _ARABIC_DIACRITICS.sub("", text)
    text = re.sub(r"[إأآا]", "ا", text)
    text = re.sub(r"ى", "ي", text)
    text = re.sub(r"ة", "ه", text)
    text = re.sub(r"[^\w\s\u0600-\u06FF]", " ", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text
