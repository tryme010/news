"""Registry of known source domains and their trust tier.

Extend this list over time. Unknown domains default to Tier 4 (unknown/local)
and social platforms default to Tier 5, per the source-quality rules
(spec section 11). This is intentionally simple/configurable rather than
hardcoded logic scattered through the codebase.
"""
from __future__ import annotations

from typing import Dict
from urllib.parse import urlparse

TIER_1_DOMAINS = {
    "reuters.com", "apnews.com", "afp.com", "un.org", "who.int",
}
TIER_2_DOMAINS = {
    "bbc.com", "bbc.co.uk", "aljazeera.com", "aljazeera.net", "cnn.com",
    "nytimes.com", "theguardian.com", "washingtonpost.com", "ft.com",
    "bloomberg.com", "wsj.com", "aa.com.tr", "asharq.com", "skynewsarabia.com",
    "cnbc.com",
}
TIER_3_DOMAINS = {
    "techcrunch.com", "theverge.com", "wired.com", "arabnews.com",
    "gulfnews.com", "thenationalnews.com", "espn.com", "variety.com",
}
SOCIAL_DOMAINS = {
    "twitter.com", "x.com", "facebook.com", "tiktok.com", "instagram.com",
    "reddit.com", "t.me",
}

TIER_CREDIBILITY = {1: 0.95, 2: 0.8, 3: 0.65, 4: 0.4, 5: 0.15}


def domain_of(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:  # noqa: BLE001
        return ""


def classify_domain(url: str) -> Dict:
    domain = domain_of(url)
    is_gov = domain.endswith(".gov") or domain.endswith(".gov.ae") or domain.endswith(".gov.sa")
    is_edu = domain.endswith(".edu") or ".edu." in domain
    if is_gov or is_edu or domain in TIER_1_DOMAINS:
        tier = 1
    elif domain in TIER_2_DOMAINS:
        tier = 2
    elif domain in TIER_3_DOMAINS:
        tier = 3
    elif domain in SOCIAL_DOMAINS:
        tier = 5
    else:
        tier = 4
    return {"domain": domain, "tier": tier, "credibility_score": TIER_CREDIBILITY[tier]}
