# Telegram Setup

The pipeline sends a daily report (candidates, verified events, articles,
drafts, distribution, draft links) and immediate error alerts to Telegram.

## 1. Create a bot

1. Open Telegram, message **@BotFather**.
2. Send `/newbot`, follow the prompts (name + username).
3. BotFather replies with a token like `123456789:AAExampleTokenXXXXXXXXXXXXXXXXXXXXX`.
   This is `TELEGRAM_BOT_TOKEN`.

## 2. Obtain your chat ID

Option A — personal chat:
1. Message your new bot anything (e.g. "hi").
2. Visit `https://api.telegram.org/bot<TOKEN>/getUpdates` in a browser.
3. Find `"chat":{"id": ...}` in the JSON response — that number is
   `TELEGRAM_CHAT_ID`.

Option B — a group/channel:
1. Add the bot to the group/channel as a member (channels: as admin).
2. Send a message in the group.
3. Same `getUpdates` call as above; group chat IDs are negative numbers.

## 3. Configure GitHub Secrets

Repository → **Settings → Secrets and variables → Actions**:

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

## 4. Test the notification

```bash
TELEGRAM_BOT_TOKEN=... TELEGRAM_CHAT_ID=... python3 -c "
from src.telegram.reporter import send_daily_report
send_daily_report(
    {'date': '2026-09-04', 'candidates_found': 10, 'events_verified': 5,
     'rejected': 2, 'duplicates_removed': 3, 'articles_generated': 5,
     'drafts_created': 5, 'errors': 0},
    {'General News': 3, 'Technology': 2},
    ['General News: https://example.blogspot.com/draft1'],
)
"
```

You should receive a formatted report message in the configured chat.
Error alerts use `src.telegram.reporter.send_error_alert` the same way and
fire automatically whenever the pipeline records article-level errors.
