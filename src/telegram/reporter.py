"""Telegram daily report + error alert sender."""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

import requests

from src.utils.retry import retry_with_backoff

logger = logging.getLogger("news_bot.telegram")

API_BASE = "https://api.telegram.org"


def _send_message(text: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat_id:
        logger.warning("TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID not configured; skipping Telegram send.")
        return False

    def _call():
        resp = requests.post(
            f"{API_BASE}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML",
                  "disable_web_page_preview": True},
            timeout=15,
        )
        if resp.status_code >= 400:
            raise RuntimeError(f"Telegram send failed ({resp.status_code}): {resp.text[:300]}")
        return True

    try:
        return retry_with_backoff(_call, max_attempts=2)
    except Exception as exc:  # noqa: BLE001
        logger.error("Telegram send failed (non-fatal, drafts already created): %s", exc)
        return False


def send_daily_report(stats: Dict, distribution: Dict[str, int], draft_links: List[str],
                       max_links: int = 40) -> bool:
    date_str = stats.get("date", "")
    lines = [
        "📰 <b>Daily News Automation Report</b>",
        f"Date: {date_str}",
        "",
        f"Candidates discovered: {stats.get('candidates_found', 0)}",
        f"Verified events: {stats.get('events_verified', 0)}",
        f"Rejected: {stats.get('rejected', 0)}",
        f"Duplicates removed: {stats.get('duplicates_removed', 0)}",
        "",
        f"Articles generated: {stats.get('articles_generated', 0)}",
        f"Blogger drafts created: {stats.get('drafts_created', 0)}",
        "",
        "Distribution:",
    ]
    for site_name, count in distribution.items():
        lines.append(f"  {site_name}: {count}")
    lines.append("")
    lines.append(f"Errors: {stats.get('errors', 0)}")

    if draft_links:
        lines.append("")
        lines.append("Draft links:")
        for link in draft_links[:max_links]:
            lines.append(link)
        if len(draft_links) > max_links:
            lines.append(f"...and {len(draft_links) - max_links} more.")

    return _send_message("\n".join(lines))


def send_error_alert(component: str, problem: str, run_id: str = "", articles_affected: int = 0) -> bool:
    text = (
        "🚨 <b>News Bot Error</b>\n\n"
        f"Component: {component}\n"
        f"Problem: {problem}\n"
        f"Run ID: {run_id}\n"
        f"Articles affected: {articles_affected}"
    )
    return _send_message(text)
