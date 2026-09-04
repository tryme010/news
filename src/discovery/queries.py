"""Generate multilingual search queries for a topic.

Discovery scope is global/multilingual; the final article is always Arabic
(see spec section 8 & 67). This module only builds query strings — actual
fetching happens in search_engine.py / rss.py.
"""
from __future__ import annotations

from typing import Dict, List


def build_queries(topic: Dict) -> List[str]:
    name = topic["name"]
    ar_templates = [
        f"أحدث أخبار {name}",
        f"آخر تطورات {name}",
    ]
    en_templates = [
        f"latest {name} news",
        f"{name} news today",
    ]
    queries = ar_templates + en_templates
    for kw in topic.get("keywords", []):
        queries.append(kw)
    # de-duplicate while preserving order
    seen = set()
    unique = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            unique.append(q)
    return unique
