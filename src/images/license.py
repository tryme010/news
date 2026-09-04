"""Track/validate image licensing so we never publish an unlicensed image."""
from __future__ import annotations

APPROVED_LICENSES = {
    "cc0", "public_domain", "editorial_use", "ai_generated", "royalty_free",
    "unsplash_license", "pexels_license",
}


def is_license_approved(license_name: str) -> bool:
    return (license_name or "").strip().lower() in APPROVED_LICENSES
