"""Blogger API v3 OAuth2 authentication.

Uses a long-lived refresh token to mint short-lived access tokens at runtime.
The refresh token MUST have been granted the full Blogger scope:
https://www.googleapis.com/auth/blogger
"""
from __future__ import annotations

import os
from typing import Dict

import requests

from src.utils.retry import retry_with_backoff

TOKEN_URL = "https://oauth2.googleapis.com/token"
TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
BLOGGER_SCOPE = "https://www.googleapis.com/auth/blogger"


class BloggerAuthError(RuntimeError):
    pass


def _token_request() -> Dict:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    refresh_token = os.environ.get("GOOGLE_REFRESH_TOKEN", "").strip()

    if not (client_id and client_secret and refresh_token):
        raise BloggerAuthError(
            "Missing Blogger/Google OAuth credentials. Set GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN."
        )

    def _call():
        resp = requests.post(
            TOKEN_URL,
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            raise BloggerAuthError(
                f"Token refresh failed ({resp.status_code}): {resp.text[:500]}"
            )
        return resp.json()

    return retry_with_backoff(_call, max_attempts=3)


def _validate_blogger_scope(access_token: str, token_payload: Dict) -> None:
    """Fail early with a useful message if the refresh token lacks write scope."""
    scope_text = str(token_payload.get("scope", "")).strip()

    # Google normally returns scope on the token response. If it is absent,
    # tokeninfo gives us the authoritative granted scopes for this access token.
    if not scope_text:
        try:
            info = requests.get(
                TOKENINFO_URL,
                params={"access_token": access_token},
                timeout=10,
            )
            if info.ok:
                scope_text = str(info.json().get("scope", "")).strip()
        except requests.RequestException:
            # Do not turn a temporary diagnostic failure into an auth failure;
            # Blogger itself will still return the definitive authorization error.
            return

    scopes = set(scope_text.split())
    if BLOGGER_SCOPE not in scopes:
        raise BloggerAuthError(
            "The Google refresh token does not have Blogger write permission. "
            f"Required scope: {BLOGGER_SCOPE}. Granted scopes: "
            f"{scope_text or 'unknown'}. Regenerate GOOGLE_REFRESH_TOKEN with "
            "the full Blogger scope and replace the GitHub secret."
        )


def get_access_token() -> str:
    payload = _token_request()
    access_token = str(payload.get("access_token", "")).strip()
    if not access_token:
        raise BloggerAuthError("Google OAuth token response did not contain access_token.")

    _validate_blogger_scope(access_token, payload)
    return access_token
