# accounts/utils.py

from __future__ import annotations

import logging

from django.http import HttpRequest

logger = logging.getLogger("apps.accounts")


def get_client_ip(request: HttpRequest) -> str | None:
    """
    Extract real client IP from request.

    Checks X-Forwarded-For first — handles requests
    passing through Nginx reverse proxy or load balancer.
    Falls back to REMOTE_ADDR for direct connections.
    """
    forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded_for:
        # X-Forwarded-For can be a comma-separated list
        # First IP is always the original client
        return forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def get_user_agent(request: HttpRequest) -> str:
    """
    Extract user agent string from request headers.
    Returns empty string if not present.
    """
    return request.META.get("HTTP_USER_AGENT", "")


def log_login_activity(
    request: HttpRequest,
    email: str,
    was_successful: bool,
    user=None,
    failure_reason: str = "",
) -> None:
    """
    Creates a UserLoginActivity record for every login attempt.

    Imported inside function to avoid circular imports since
    utils.py is imported by models.py indirectly via signals.

    Args:
        request:        The incoming HTTP request.
        email:          Email submitted in the login form.
        was_successful: True if login succeeded.
        user:           User instance if login succeeded. None otherwise.
        failure_reason: Short failure code if login failed.
    """
    from apps.accounts.models import UserLoginActivity

    try:
        UserLoginActivity.objects.create(
            user=user,
            email_attempted=email,
            ip_address=get_client_ip(request),
            user_agent=get_user_agent(request),
            was_successful=was_successful,
            failure_reason=failure_reason,
        )
    except Exception:
        # Never let activity logging break the login flow
        logger.exception(
            "Failed to write login activity log",
            extra={"email": email, "was_successful": was_successful},
        )