"""Daily run orchestrator implementing the algorithm in spec section 56:

topics -> discovery -> normalize -> dedup -> events -> verify -> rank ->
select -> distribute -> write -> fact-check -> quality gate -> image ->
Blogger draft -> persist -> Telegram report.
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict, List

from src.ai.provider import get_ai_provider
from src.blogger.client import BloggerClient
from src.blogger.drafts import create_draft_for_article
from src.database.models import Article, Event, RunStats, Source
from src.database.repository import Repository
from src.deduplication.similarity import group_candidates_into_events
from src.discovery.candidate_builder import discover_candidates
from src.distribution.allocator import allocate_event_to_websites
from src.images.image_metadata import to_image_asset
from src.images.image_selector import select_image
from src.pipeline.demo_fixtures import build_demo_candidates
from src.pipeline.topic_rotation import select_topics_for_run
from src.telegram.reporter import send_daily_report, send_error_alert
from src.utils.logging import setup_logging
from src.utils.time import utcnow_iso
from src.verification.verifier import verify_event_group
from src.writer.article_generator import generate_article
from src.writer.fact_checker import run_fact_check
from src.writer.seo import generate_seo


def load_json_config(path: str) -> List[Dict] | Dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def compute_quality_score(verification_score: float, avg_source_credibility: float,
                           word_count: int, min_words: int, max_words: int,
                           fact_check_passed: bool, editorial_relevance: float,
                           weights: Dict) -> float:
    factual_accuracy = verification_score  # 0-100
    source_quality = avg_source_credibility * 100
    recency = 100  # candidates already filtered by recency upstream
    originality = 90 if fact_check_passed else 40
    length_ok = min_words <= word_count <= max_words * 1.15
    readability = 85 if length_ok else 55
    headline_quality = 80
    duplicate_risk_penalty = 0  # dedup already applied before this point

    score = (
        weights["factual_accuracy"] * factual_accuracy
        + weights["source_quality"] * source_quality
        + weights["recency"] * recency
        + weights["originality"] * originality
        + weights["readability"] * readability
        + weights["editorial_relevance"] * editorial_relevance
        + weights["headline_quality"] * headline_quality
        - weights["duplicate_risk_penalty"] * duplicate_risk_penalty
    )
    return round(min(100.0, max(0.0, score)), 1)


def run_pipeline(dry_run: bool = False, demo_mode: bool = False, db_path: str = "data/news.db") -> Dict:
    logger = setup_logging(run_id="pipeline")
    settings = load_json_config("config/settings.json")
    topics = load_json_config("config/topics.json")
    websites = load_json_config("config/websites.json")

    repo = Repository(db_path)
    run = RunStats(dry_run=dry_run, demo_mode=demo_mode)
    repo.insert_run(run)

    ai = get_ai_provider()
    blogger_client = BloggerClient(dry_run=dry_run)

    topic_by_id = {t["id"]: t for t in topics}

    rotation_cfg = settings["rotation"]
    selected_topics = select_topics_for_run(
        topics, repo,
        min_topics=rotation_cfg["topics_per_run_min"],
        max_topics=rotation_cfg["topics_per_run_max"],
        randomness_factor=rotation_cfg["randomness_factor"],
    )
    run.topics_processed = len(selected_topics)

    # ---------------- discovery ----------------
    if demo_mode:
        candidates = build_demo_candidates(selected_topics)
    else:
        candidates = discover_candidates(selected_topics, demo_mode=False)
    run.candidates_found = len(candidates)

    # ---------------- deduplication -> events ----------------
    dedup_cfg = settings["deduplication"]
    groups = group_candidates_into_events(
        candidates,
        similarity_threshold=dedup_cfg["similarity_threshold"],
        time_window_hours=dedup_cfg["fingerprint_time_window_hours"],
    )
    run.duplicates_removed = max(0, len(candidates) - len(groups))

    # ---------------- verification ----------------
    verification_cfg = settings["verification"]
    verified_events: List[Dict] = []
    rejected_count = 0

    for group in groups:
        if not group:
            continue
        verdict = verify_event_group(group, ai, verification_cfg["min_score_to_publish"])
        if not verdict.get("passes_publish_bar", False):
            rejected_count += 1
            continue

        rep = group[0]
        source_ids = []
        for cand in group:
            src = Source(
                url=cand["url"], domain=cand.get("domain", ""), title=cand.get("title", ""),
                published_at=cand.get("published_at"), source_tier=cand.get("source_tier", 4),
                credibility_score=cand.get("credibility_score", 0.4),
            )
            source_ids.append(repo.upsert_source(src))

        event = Event(
            topic_id=rep.get("topic_id", ""),
            title=rep.get("title", ""),
            summary=rep.get("summary", ""),
            fingerprint=rep.get("_fingerprint", ""),
            region=rep.get("region", "Global"),
            country=rep.get("country", ""),
            entities=rep.get("entities", []),
            source_ids=source_ids,
            verification_score=verdict["verification_score"],
            status=verdict["recommended_status"],
            is_sensitive=verdict.get("is_sensitive", False),
        )

        existing = repo.find_event_by_fingerprint(event.fingerprint)
        if existing:
            continue  # idempotency: already processed this event before

        repo.insert_event(event)
        verified_events.append({"event": event, "sources": group})

    run.events_verified = len(verified_events)

    # rank by verification score, most recent first (recency already
    # enforced upstream by discovery); apply daily cap
    verified_events.sort(key=lambda e: e["event"].verification_score, reverse=True)
    max_daily = settings["daily_targets"]["max_daily_articles"]
    verified_events = verified_events[:max_daily]

    # ---------------- distribution + writing + images + blogger ----------------
    dist_cfg = settings["distribution"]
    quality_cfg = settings["quality"]
    article_cfg = settings["article"]
    images_cfg = settings["images"]

    current_counts: Dict[str, int] = {}
    website_id_to_name = {w["id"]: w["name"] for w in websites}
    draft_links: List[str] = []
    articles_generated = 0
    drafts_created = 0
    errors = 0

    for item in verified_events:
        event: Event = item["event"]
        sources = item["sources"]
        topic_meta = topic_by_id.get(event.topic_id, {})
        event_dict = {
            "title": event.title, "summary": event.summary, "region": event.region,
            "country": event.country, "entities": event.entities,
            "is_sensitive": event.is_sensitive,
            "topic_preferred_sites": topic_meta.get("preferred_sites", []),
        }

        allocations = allocate_event_to_websites(
            event_dict, websites, current_counts,
            min_relevance_score=dist_cfg["min_relevance_score_to_assign"],
            max_sites_per_event=dist_cfg["max_sites_per_event"],
            balance_weight=dist_cfg["network_balance_weight"],
        )

        for alloc in allocations:
            website = alloc["website"]
            if repo.article_exists(event.id, website["id"]):
                continue  # idempotency guard

            try:
                generated = generate_article(
                    event_dict, website, sources, ai,
                    min_words=article_cfg["min_words"], max_words=article_cfg["max_words"],
                )
                fact_check = run_fact_check(generated["body"], sources, ai)
                seo = generate_seo(generated["body"], generated["headline"], website["name"], ai)

                avg_credibility = sum(s.get("credibility_score", 0.4) for s in sources) / len(sources)
                quality_score = compute_quality_score(
                    event.verification_score, avg_credibility, generated["word_count"],
                    article_cfg["min_words"], article_cfg["max_words"],
                    fact_check["passed"], alloc["adjusted_score"], quality_cfg["weights"],
                )

                articles_generated += 1

                if quality_score < quality_cfg["min_quality_score"] or not fact_check["passed"]:
                    logger.info("Article below quality bar or failed fact-check; not sent to Blogger.",
                                extra={"extra_fields": {"quality_score": quality_score,
                                                         "fact_check_passed": fact_check["passed"]}})
                    continue

                article = Article(
                    event_id=event.id, website_id=website["id"],
                    title=generated["headline"], slug=seo["slug"], summary=generated["summary"],
                    body=fact_check.get("corrected_body") or generated["body"],
                    seo_title=seo["seo_title"], meta_description=seo["meta_description"],
                    keywords=seo["keywords"], quality_score=quality_score,
                    fingerprint=f"{event.fingerprint}:{website['id']}",
                )
                repo.insert_article(article)

                image_dict = select_image(
                    generated["headline"], category=_category_for_website(website),
                    region=event.region,
                    allow_ai_generated=images_cfg["allow_ai_generated_fallback"],
                    allow_missing=images_cfg["allow_missing_image"],
                )
                image_asset = to_image_asset(article.id, image_dict)
                if image_asset:
                    repo.insert_image(image_asset)

                sources_html = "المصادر: " + "، ".join(sorted({s.get("domain", "") for s in sources if s.get("domain")}))
                created = create_draft_for_article(
                    article, website, repo, blogger_client, image_asset, sources_html,
                )
                if created:
                    drafts_created += 1
                    current_counts[website["id"]] = current_counts.get(website["id"], 0) + 1
                    if article.blogger_url:
                        draft_links.append(f"{website['name']}: {article.blogger_url}")

            except Exception as exc:  # noqa: BLE001
                errors += 1
                repo.log_error(run.id, "article_pipeline", str(exc))
                logger.error("Article pipeline failed for event %s / site %s: %s",
                             event.id, website["id"], exc)
                continue

    run.articles_generated = articles_generated
    run.drafts_created = drafts_created
    run.errors = errors
    run.finished_at = utcnow_iso()
    repo.finalize_run(run)

    stats = {
        "date": utcnow_iso()[:10],
        "candidates_found": run.candidates_found,
        "events_verified": run.events_verified,
        "rejected": rejected_count,
        "duplicates_removed": run.duplicates_removed,
        "articles_generated": run.articles_generated,
        "drafts_created": run.drafts_created,
        "errors": run.errors,
    }
    distribution_report = {website_id_to_name.get(k, k): v for k, v in current_counts.items()}

    if not dry_run:
        send_daily_report(stats, distribution_report, draft_links)
        if errors > 0:
            send_error_alert("pipeline", f"{errors} article(s) failed during processing", run.id, errors)
    else:
        logger.info("DRY_RUN active: skipping Telegram report send (stats logged instead).",
                     extra={"extra_fields": stats})

    repo.close()
    return {"run": run, "stats": stats, "distribution": distribution_report, "draft_links": draft_links}


def _category_for_website(website: Dict) -> str:
    focus = " ".join(website.get("editorial_focus", [])).lower()
    if "tech" in focus or "ai" in focus or "cyber" in focus:
        return "technology"
    if "business" in focus or "econom" in focus or "market" in focus:
        return "business"
    if "sport" in focus:
        return "sports"
    if "health" in focus:
        return "health"
    if "culture" in focus or "art" in focus or "cinema" in focus:
        return "culture"
    if "education" in focus or "research" in focus:
        return "education"
    return "general"
