# Automated Arabic & Global News Network

A production-oriented automated newsroom that discovers real news globally,
verifies and deduplicates it, writes original Arabic articles, and creates
**Blogger drafts** (never auto-published) across a network of up to 10
websites — once per day, via GitHub Actions.

> **Human-in-the-loop by design.** The bot never publishes. It prepares
> drafts; a human reviews and publishes them.

---

## What it does, end to end

```
Topic rotation → Multilingual discovery → URL/title normalization
→ Deduplication (one event, many sources) → AI verification
→ Ranking + daily cap (70–150 total) → Website distribution scoring
→ Original Arabic article generation (per-site editorial angle)
→ Final fact-check → Quality gate → Licensed/fallback image
→ Blogger DRAFT creation → Telegram report → Persist state
```

See `MASTER PROMPT` history / code docstrings for the full rationale behind
each stage; the code is organized so each stage is a separate, testable
module under `src/`.

## Architecture

```
config/            topics.json, websites.json, settings.json, prompts/
src/ai/             provider-agnostic AI abstraction (mock/anthropic/openai)
src/discovery/      RSS + search-engine candidate discovery, multilingual queries
src/research/       optional deep-fetch of full article text
src/deduplication/  URL/title normalization, event fingerprinting, similarity grouping
src/verification/   cheap rule prefilter + AI verification scoring
src/writer/         Arabic article generation, SEO metadata, final fact-check
src/images/         licensed image search, AI-gen fallback, static fallback
src/distribution/   per-website relevance scoring, network balancing, allocation
src/blogger/        OAuth, draft-only Blogger API client
src/telegram/       daily report + error alerts
src/database/       SQLite models, repository (idempotent), migrations
src/pipeline/       topic rotation + orchestrator (the daily run algorithm)
tests/              pytest suite covering the above
.github/workflows/  daily-news.yml (scheduled + manual dispatch)
```

## Why SQLite + repository-backed persistence

GitHub Actions runners are ephemeral — nothing on disk survives between
runs unless you explicitly persist it. For this MVP, the chosen strategy is:

1. `data/news.db` (SQLite) is checked out with the repo at the start of each
   run (already present from the previous run's commit).
2. The pipeline reads/writes to it normally during the run.
3. At the end of the workflow, `data/news.db` and `logs/` are committed and
   pushed back to the repository (see `.github/workflows/daily-news.yml`,
   step "Persist state back to repository").

This is simple, free, and sufficient for the target volume (dozens to a
few hundred rows/day). If you outgrow it, swap `src/database/repository.py`'s
`get_connection`/`Repository.__init__` for a hosted Postgres/Turso/Supabase
connection — no other module needs to change, since everything goes through
the repository layer.

## Installation (local)

```bash
git clone <your-repo-url>
cd news-automation-bot
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in what you have; everything is optional for demo mode
```

## Running locally

### Demo Mode (no external APIs at all)

Proves the whole pipeline works using mocked candidates and a mocked AI
provider — no network calls, no credentials required.

```bash
AI_PROVIDER=mock DEMO_MODE=true DRY_RUN=true python run.py
```

You should see JSON stats printed (candidates found, events verified,
articles generated, drafts created) and a distribution breakdown.

### Dry Run (real discovery/AI, no Blogger writes)

Runs real discovery, verification, writing, and distribution, but does
**not** create Blogger drafts — it logs what would have been created.
Requires at minimum `AI_PROVIDER` + `AI_API_KEY`; search/image providers
are optional (discovery/imagery degrade gracefully without them).

```bash
AI_PROVIDER=anthropic AI_API_KEY=sk-ant-... DRY_RUN=true python run.py
```

### Production run

Same as above with `DRY_RUN=false` and Blogger + Telegram credentials set
(see `BLOGGER_SETUP.md` / `TELEGRAM_SETUP.md`). **Start with
`MAX_DAILY_ARTICLES` small (e.g. 5)** for your first live test — see
`GITHUB_SETUP.md` step 9.

## Environment variables

See `.env.example` for the full list. Summary:

| Variable | Required for | Notes |
|---|---|---|
| `AI_PROVIDER` | always | `mock` \| `anthropic` \| `openai` |
| `AI_API_KEY` | anthropic/openai | never commit |
| `SEARCH_PROVIDER`, `SEARCH_API_KEY` | real discovery | `newsapi` \| `bing`; optional — RSS still works without it |
| `IMAGE_SEARCH_PROVIDER`, `IMAGE_SEARCH_API_KEY` | licensed photos | `unsplash` \| `pexels`; optional — static fallback used otherwise |
| `IMAGE_GEN_PROVIDER`, `IMAGE_GEN_API_KEY` | AI image fallback | optional, extension point (not wired to a vendor by default) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | reporting | optional but recommended |
| `GOOGLE_CLIENT_ID/SECRET/REFRESH_TOKEN` | Blogger drafts | see `BLOGGER_SETUP.md` |
| `DRY_RUN`, `DEMO_MODE` | testing | `true`/`false` |
| `MIN/TARGET/MAX_DAILY_ARTICLES` | volume control | mirrors `config/settings.json` |

## Database

SQLite at `data/news.db`. Tables: `topics, events, sources, event_sources,
articles, article_sources, websites, runs, images, errors` (see
`src/database/migrations.py` for full schema).

## AI providers

`AI_PROVIDER=mock` needs nothing and is used for tests/demo. `anthropic`
and `openai` are real, working adapters (`src/ai/anthropic_provider.py`,
`src/ai/openai_provider.py`) — add a real API key and you're live. Add a
new provider by implementing `src/ai/base.py`'s `AIProvider` interface and
registering it in `src/ai/provider.py`.

## Blogger / Telegram / GitHub Actions setup

See `BLOGGER_SETUP.md`, `TELEGRAM_SETUP.md`, `GITHUB_SETUP.md`.

## Testing

```bash
AI_PROVIDER=mock python -m pytest tests/ -v
```

24 tests cover: URL/title normalization, event fingerprinting, duplicate
grouping, verification scoring/thresholds, website scoring, network
balancing, allocation limits, idempotency (article/event/source upserts),
slug generation, and a full demo+dry-run pipeline execution (twice, to
verify reruns don't duplicate output).

## Troubleshooting

- **"AI_PROVIDER requires an API key"** — set `AI_API_KEY` in your env/secrets.
- **0 articles generated** — check `logs/pipeline.log`; likely all
  candidates failed the cheap prefilter or AI verification (this is
  correct behavior on a quiet news day / with no real search provider
  configured, not a bug).
- **0 drafts created despite articles generated** — check that
  `config/websites.json` has real `blogger_blog_id` values and that
  Google OAuth env vars are set; the pipeline intentionally skips Blogger
  calls (not article generation) when a site has no blog ID configured.
- **GitHub Actions push step fails** — check branch protection rules allow
  the `github-actions` bot (or a PAT) to push directly to the branch.

## Known limitations (V1)

- No dashboard/UI (by design — see spec section 51).
- Image generation provider is a documented extension point, not wired to
  a specific vendor (no AI image-gen credentials were available while
  building this; swap in your provider in `src/images/image_generator.py`).
- Search discovery ships with NewsAPI/Bing adapters; add more in
  `src/discovery/search_engine.py` as needed.
- Persistence is repository-committed SQLite, fine for the target volume;
  swap for a hosted DB if you scale beyond ~thousands of rows.
