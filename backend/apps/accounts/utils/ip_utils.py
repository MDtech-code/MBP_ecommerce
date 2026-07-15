# apps/accounts/utils/ip_utils.py
from __future__ import annotations

import logging

logger = logging.getLogger("apps.accounts")


def get_client_ip(request) -> str | None:
    """
    Extract real client IP from request.

    Checks X-Forwarded-For first — handles requests passing through
    Nginx reverse proxy or load balancer.
    Falls back to REMOTE_ADDR for direct connections.

    Args:
        request: Django/DRF request object.

    Returns:
        IP address string or None if not determinable.
    """
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        # X-Forwarded-For can be a comma-separated list.
        # First IP is always the original client.
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_user_agent(request) -> str:
    """
    Extract user agent string from request headers.

    Args:
        request: Django/DRF request object.

    Returns:
        User agent string or empty string if not present.
    """
    return request.META.get("HTTP_USER_AGENT", "")


def log_login_activity(
    *,
    email: str,
    was_successful: bool,
    ip_address: str | None,
    user_agent: str,
    user=None,
    failure_reason: str = "",
) -> None:
    """
    Create a UserLoginActivity record for every login attempt.

    Called from service layer — receives ip_address and user_agent
    as plain strings so service has zero dependency on request object.

    Never raises — login flow must never break due to audit log failure.

    Args:
        email:          Email submitted in the login form.
        was_successful: True if login succeeded.
        ip_address:     Client IP extracted from request before service call.
        user_agent:     User agent string extracted from request.
        user:           User instance if login succeeded. None otherwise.
        failure_reason: Short failure code if login failed.
    """
    from apps.accounts.models import UserLoginActivity

    try:
        UserLoginActivity.objects.create(
            user=user,
            email_attempted=email,
            ip_address=ip_address,
            user_agent=user_agent,
            was_successful=was_successful,
            failure_reason=failure_reason,
        )
    except Exception:
        # Never let activity logging break the login flow.
        logger.exception(
            "Failed to write login activity log",
            extra={"email": email, "was_successful": was_successful},
        )