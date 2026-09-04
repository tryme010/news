# GitHub Actions Setup

## 1. Create repository

Create a new (private recommended) GitHub repository.

## 2. Clone and push this project

```bash
git clone <your-empty-repo-url> news-automation-bot
cd news-automation-bot
# copy in all project files
git add .
git commit -m "Initial commit: automated news pipeline"
git push
```

## 3. Install dependencies (for local testing before relying on Actions)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## 4. Configure secrets

Repository → **Settings → Secrets and variables → Actions → New repository secret**.
At minimum for a first (mock/demo) test, none are required. For a real
run, add:

| Secret | Purpose |
|---|---|
| `AI_API_KEY` | Anthropic or OpenAI key (matches `AI_PROVIDER`) |
| `SEARCH_API_KEY` | NewsAPI or Bing key (optional) |
| `IMAGE_SEARCH_API_KEY` | Unsplash or Pexels key (optional) |
| `IMAGE_GEN_API_KEY` | AI image generation key (optional) |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Telegram reporting |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_REFRESH_TOKEN` | Blogger drafts |

Also add **repository variables** (Settings → Secrets and variables →
Actions → Variables tab) if you want to override provider selection
without touching secrets: `AI_PROVIDER`, `SEARCH_PROVIDER`,
`IMAGE_SEARCH_PROVIDER`, `IMAGE_GEN_PROVIDER`.

## 5. Configure your 10 Blogger blog IDs

Edit `config/websites.json`, fill each site's `blogger_blog_id` (see
`BLOGGER_SETUP.md` step 6). Commit and push.

## 6. Configure topics

`config/topics.json` ships with ~60 recurring topics already. Edit
`preferred_sites`, `priority`, `regions`, or add/remove topics as needed.

## 7. Configure Telegram

See `TELEGRAM_SETUP.md`.

## 8. Test Demo Mode (GitHub Actions)

Repository → **Actions → Daily News Automation → Run workflow**. Set
`demo_mode: true`, `dry_run: true`. Confirm the run succeeds and check the
"Run news pipeline" step logs for stats (no external credentials needed
for this test).

## 9. Test Dry Run

Run the workflow again with `demo_mode: false`, `dry_run: true`, and
`AI_API_KEY` (+ optionally `SEARCH_API_KEY`) configured. Confirm real
discovery/verification/writing happens but no Blogger drafts are created.

Before your very first real run, also set `MAX_DAILY_ARTICLES=5` (as a
repository variable or by temporarily editing `config/settings.json`) so
you don't create dozens of drafts on an untested config.

## 10. Test Blogger draft creation

Run with `dry_run: false` and all Blogger secrets configured. Check the 10
Blogger blogs' **Posts → Drafts** tabs for new drafts. Raise
`MAX_DAILY_ARTICLES` back to your target (70–150) once you're satisfied.

## 11. Enable scheduled workflow

The `schedule: cron: "17 3 * * *"` trigger in
`.github/workflows/daily-news.yml` is already enabled once the workflow
file is on the default branch — no extra step needed. Adjust the cron
expression for your preferred time (GitHub Actions cron is UTC and
best-effort, not exact-to-the-minute).

## 12. Verify Telegram report

After a real (non-dry-run) scheduled or manual run, confirm you receive
the daily report message in your configured Telegram chat, including
draft links.

---

### How persistence works here

`data/news.db` and `logs/` are committed back to the repository at the end
of every workflow run (see the "Persist state back to repository" step).
This is what makes topic rotation, deduplication history, and idempotency
work across otherwise-ephemeral GitHub Actions runs. Make sure
`permissions: contents: write` (already set in the workflow) is retained,
and that branch protection on your default branch allows the Actions bot
to push (or switch to a dedicated `bot` branch + PR if your protection
rules require review).
