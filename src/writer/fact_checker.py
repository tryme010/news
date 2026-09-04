"""Final fact-checking pass before an article becomes a Blogger draft
(spec section 23)."""
from __future__ import annotations

import json
import logging
from typing import Dict, List

from src.ai.base import AIProvider

logger = logging.getLogger("news_bot.writer.fact_checker")


def _load_prompt_template() -> str:
    with open("config/prompts/fact_check.txt", "r", encoding="utf-8") as f:
        return f.read()


def run_fact_check(article_body: str, sources: List[Dict], ai: AIProvider) -> Dict:
    template = _load_prompt_template()
    source_material = [
        {"title": s.get("title"), "summary": s.get("summary", "")[:600]}
        for s in sources
    ]
    prompt = (
        f"{template}\n\nARTICLE BODY:\n{article_body}\n\n"
        f"SOURCE MATERIAL:\n{json.dumps(source_material, ensure_ascii=False)}"
    )
    try:
        result = ai.generate_json(prompt, max_tokens=1200, temperature=0.1)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Fact check failed, treating as not-passed: %s", exc)
        return {"passed": False, "issues": [{"type": "other", "description": str(exc), "severity": "high"}]}

    high_severity = [i for i in result.get("issues", []) if i.get("severity") == "high"]
    passed = result.get("passed", False) and not high_severity
    return {
        "passed": passed,
        "issues": result.get("issues", []),
        "corrected_body": result.get("corrected_body"),
    }
