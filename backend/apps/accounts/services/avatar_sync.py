# apps/accounts/services/avatar_sync.py
from __future__ import annotations

import logging
from urllib.parse import urlparse

import requests
from django.core.files.base import ContentFile

logger = logging.getLogger("apps.accounts")

# Guard against a provider URL redirecting somewhere unexpectedly large —
# no legitimate OAuth provider avatar should exceed this.
MAX_AVATAR_BYTES = 5 * 1024 * 1024  # 5MB

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}


def sync_provider_avatar(*, user_profile, avatar_url: str) -> bool:
    """
    Download a social provider's avatar URL and save it into
    UserProfile.avatar (an ImageField — cannot be assigned a URL string
    directly, which is why this exists rather than a one-line assignment).

    Called ONLY on new-account creation (Case 3 in
    login_or_register_social_user) — never on returning-user or
    account-linking logins. This is a deliberate product decision: a
    user's own uploaded avatar should never be silently overwritten by
    their Google/Facebook photo on a later login. If that behavior is
    ever wanted, it needs to be an explicit user action ("sync my Google
    photo"), not an automatic side effect of login.

    Failure here is non-fatal by design, same philosophy as
    _dispatch_verification_email in the registration service — a failed
    avatar download must never block account creation. The user simply
    ends up with no avatar, exactly as if they'd registered manually and
    not uploaded one; nothing about their account is broken or
    incomplete because of this.

    Args:
        user_profile: The UserProfile instance to update.
        avatar_url: URL from SocialUserData.avatar_url. May be empty
            string (provider gave none) — handled as a no-op.

    Returns:
        True if the avatar was successfully downloaded and saved,
        False otherwise (empty URL, download failure, invalid content
        type, oversized response). Callers can log or ignore this.
    """
    if not avatar_url:
        return False

    try:
        response = requests.get(avatar_url, timeout=10, stream=True)
    except requests.RequestException:
        logger.warning(
            "Avatar sync — failed to fetch provider avatar",
            extra={"user_id": user_profile.user_id, "avatar_url": avatar_url},
        )
        return False

    if response.status_code != 200:
        logger.warning(
            "Avatar sync — provider avatar URL returned non-200",
            extra={
                "user_id": user_profile.user_id,
                "status_code": response.status_code,
            },
        )
        return False

    content_type = response.headers.get("Content-Type", "").split(";")[0].strip()
    extension = ALLOWED_CONTENT_TYPES.get(content_type)
    if not extension:
        logger.warning(
            "Avatar sync — unexpected content type, skipping",
            extra={"user_id": user_profile.user_id, "content_type": content_type},
        )
        return False

    content_length = response.headers.get("Content-Length")
    if content_length and int(content_length) > MAX_AVATAR_BYTES:
        logger.warning(
            "Avatar sync — provider avatar exceeds size limit, skipping",
            extra={"user_id": user_profile.user_id, "content_length": content_length},
        )
        return False

    # Content-Length header isn't always present/trustworthy — enforce
    # the real limit while actually reading the body, not just trusting
    # the header.
    content = response.raw.read(MAX_AVATAR_BYTES + 1, decode_content=True)
    if len(content) > MAX_AVATAR_BYTES:
        logger.warning(
            "Avatar sync — provider avatar body exceeded size limit, skipping",
            extra={"user_id": user_profile.user_id},
        )
        return False

    filename = f"{urlparse(avatar_url).netloc or 'social'}_avatar.{extension}"
    user_profile.avatar.save(filename, ContentFile(content), save=True)

    logger.info(
        "Avatar sync — provider avatar saved",
        extra={"user_id": user_profile.user_id},
    )
    return True