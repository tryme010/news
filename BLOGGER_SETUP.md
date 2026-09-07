# Blogger API Setup

The pipeline creates **draft-only** posts via the Blogger API v3. It never
publishes automatically (`isDraft=true` is hardcoded in
`src/blogger/client.py`).

## 1. Create a Google Cloud project

1. Go to https://console.cloud.google.com/
2. Create a new project (e.g. "news-automation-bot").

## 2. Enable the Blogger API

1. In the project, go to **APIs & Services → Library**.
2. Search for **Blogger API v3** and click **Enable**.

## 3. Configure OAuth consent screen

1. **APIs & Services → OAuth consent screen**.
2. Choose **External** (or **Internal** if using Google Workspace).
3. Fill in the required app name/support email. You can leave it in
   "Testing" mode and add your own Google account as a test user — this
   project only ever needs one authorized account (the one that owns/edits
   the 10 Blogger blogs).

## 4. Create OAuth credentials

1. **APIs & Services → Credentials → Create Credentials → OAuth client ID**.
2. Application type: **Desktop app**.
3. Save the generated **Client ID** and **Client Secret** — these become
   `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET`.

## 5. Obtain a refresh token (one-time, manual)

Run this locally once (requires `google-auth-oauthlib`, not a project
dependency — install it just for this step: `pip install google-auth-oauthlib`):

```python
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/blogger"]

flow = InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": "YOUR_CLIENT_ID",
            "client_secret": "YOUR_CLIENT_SECRET",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    },
    scopes=SCOPES,
)
creds = flow.run_local_server(port=0)
print("Refresh token:", creds.refresh_token)
```

This opens a browser, asks you to sign in with the Google account that
owns/edits the 10 Blogger blogs, and prints a refresh token. Save it as
`GOOGLE_REFRESH_TOKEN`. It does not expire under normal use (only if
revoked or unused for 6 months).

## 6. If you get Blogger 403 PERMISSION_DENIED

A `403: The caller does not have permission` during `posts.insert` is not a news/distribution problem. It means the Google identity used by `GOOGLE_REFRESH_TOKEN` cannot write to that specific Blogger blog, or the refresh token was created without the full Blogger write scope. The code now checks the token scope and blog access before attempting the write.

Fix it in this order:

1. Make sure the Google account used during OAuth is an **owner/admin/editor** of every active Blogger blog.
2. Regenerate the refresh token using the exact OAuth scope `https://www.googleapis.com/auth/blogger` from the script in Step 5.
3. Replace the `GOOGLE_REFRESH_TOKEN` GitHub Actions secret with the new token.
4. Make sure every active `blogger_blog_id` is the ID of a blog that this same Google account can edit.
5. Run one manual workflow with `DRY_RUN=false`.

The refresh token cannot be upgraded from read-only to write access by changing Python code; Google must issue a new token with the correct scope.

## 6. Obtain your 10 Blog IDs

For each Blogger blog:

1. Go to https://www.blogger.com/, open the blog.
2. **Settings → Basic** shows the Blog ID in the URL, or call:
   `GET https://www.googleapis.com/blogger/v3/blogs/byurl?url=<blog-url>&key=<api-key>`
3. Fill each blog's `blogger_blog_id` field in `config/websites.json`.

## 7. Add GitHub Secrets

Repository → **Settings → Secrets and variables → Actions → New repository secret**:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`

## 8. Test draft creation

```bash
GOOGLE_CLIENT_ID=... GOOGLE_CLIENT_SECRET=... GOOGLE_REFRESH_TOKEN=... \
AI_PROVIDER=mock DEMO_MODE=true DRY_RUN=false python run.py
```

With `DRY_RUN=false` and real Blogger credentials + real `blogger_blog_id`
values in `config/websites.json`, this creates real drafts on your blogs
(still using mocked demo article content). Check each blog's **Posts →
Drafts** tab in the Blogger dashboard to confirm — nothing should appear
under "Published".

## 9. Verify nothing is published automatically

Every draft created by `src/blogger/client.py::create_draft` passes
`isDraft=true`. There is no code path in this project that calls the
Blogger "publish" endpoint. You publish manually from the Blogger
dashboard after review.


## Multi-blog daily quotas
The pipeline targets 7-15 articles per active blog per day (10 target). Each active blog MUST have its own unique `blogger_blog_id`. The same Google OAuth refresh token may be shared when the same Google account has access to all blogs, but the Blogger blog IDs themselves must be different.

With 10 active blogs the network target is 70-150 articles/day (100 target). With 6 active blogs it is 42-90/day.
