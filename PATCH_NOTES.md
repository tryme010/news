# Single-source + Blogger 403 fix

Changes:
- One credible source is sufficient; no hard 2-source requirement, including sensitive stories.
- AI verification still checks reality, recency, newsworthiness, attribution, and source support.
- Blogger OAuth/403 handling is included from the previous fix.
- RSS `feed_topic_hint` is honored before keyword matching, fixing broad world-news items being dropped from discovery.

Validation:
- pytest: 29 passed
- compileall: passed

Do not copy any secrets or client-secret files from this patch into GitHub.
