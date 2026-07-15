# apps/accounts/utils/token_utils.py
from __future__ import annotations

import logging

logger = logging.getLogger("apps.accounts")


def blacklist_all_user_tokens(user: "User") -> None:
    """
    Blacklist all outstanding JWT refresh tokens for a given user.

    Called after:
        - Password reset confirmed
        - Password changed
        - Email changed

    Why all three?
        All three operations change login credentials.
        Any existing session after a credential change is a
        potential security risk — force re-login on all devices.

    Non-fatal by design:
        Caller wraps this in try/except and logs failure.
        The critical operation (password/email change) is already
        committed before this runs — failure here must never
        roll back or block the success response.

    Args:
        user: The User whose tokens should be blacklisted.
    """
    from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
    from rest_framework_simplejwt.tokens import RefreshToken

    outstanding_tokens = OutstandingToken.objects.filter(user=user)

    for token in outstanding_tokens:
        try:
            refresh = RefreshToken(token.token)
            refresh.blacklist()
        except Exception:
            # Individual token failure — log and continue.
            # Blacklist as many as possible, never stop on first failure.
            logger.warning(
                "Failed to blacklist individual token during bulk invalidation",
                extra={"user_id": user.id, "token_id": token.id},
            )