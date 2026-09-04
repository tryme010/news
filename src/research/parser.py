"""Extract readable article text from fetched HTML."""
from __future__ import annotations

import re


def extract_text(html: str, max_chars: int = 6000) -> str:
    if not html:
        return ""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
            tag.decompose()
        text = soup.get_text(separator=" ")
    except ImportError:
        text = re.sub(r"<[^>]+>", " ", html)

    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars]
