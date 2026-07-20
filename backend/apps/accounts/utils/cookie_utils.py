# apps/accounts/utils/cookie_utils.py
from __future__ import annotations

from django.conf import settings
from django.middleware.csrf import get_token

# ── Cookie configuration ───────────────────────────────────────────────────────
# Centralized here so every place that touches cookies
# uses identical settings — no drift between set and clear.

REFRESH_COOKIE_NAME = "refresh_token"

COOKIE_SETTINGS = {
    "httponly": True,
    # "secure": not settings.DEBUG,   # True in production, False in local dev
    "secure":True,
    "samesite": "Lax",
    "max_age": 7 * 24 * 60 * 60,   # 7 days in seconds
    "path": "/api/accounts/",
}


def set_refresh_cookie(response, refresh_token: str) -> None:
    """
    Set the HttpOnly refresh token cookie on the response.

    Scoped to /api/accounts/token/refresh/ so the browser
    never sends it to any other endpoint — minimizes exposure.

    Args:
        response:      DRF Response object.
        refresh_token: Refresh token string to store in cookie.
    """
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        str(refresh_token),
        **COOKIE_SETTINGS,
    )


def clear_refresh_cookie(response) -> None:
    """
    Delete the refresh token cookie from the response.

    Path must match the path used when setting the cookie —
    browsers use path + name together to identify a cookie.

    Args:
        response: DRF Response object.
    """
    response.delete_cookie(
        REFRESH_COOKIE_NAME,
        path=COOKIE_SETTINGS["path"],
    )


def set_csrf_cookie(request, response) -> None:
    """
    Ensure csrftoken cookie is set and readable by JavaScript.

    httponly=False is intentional — JS must read this value
    and send it back in the X-CSRFToken header on state-changing
    requests. This is the standard CSRF double-submit pattern.

    Args:
        request:  DRF Request object.
        response: DRF Response object.
    """
    csrf_token = get_token(request)
    response.set_cookie(
        "csrftoken",
        csrf_token,
        httponly=False,         # must be accessible to JS
        secure=not settings.DEBUG,
        samesite="Lax",
    )


def clear_csrf_cookie(response) -> None:
    """
    Delete the CSRF cookie from the response.

    Scoped to root path — CSRF cookie is never path-scoped.

    Args:
        response: DRF Response object.
    """
    response.delete_cookie(
        "csrftoken",
        path="/",
    )