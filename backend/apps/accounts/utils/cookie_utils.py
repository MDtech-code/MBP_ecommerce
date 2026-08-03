# apps/accounts/utils/cookie_utils.py
from __future__ import annotations



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








EMAIL_COOKIE_NAME = "pending_verification_email"

EMAIL_COOKIE_SETTINGS = {
    "httponly": False,   
    "secure": True,      
    "samesite": "Lax",   
    "max_age": 15 * 60, 
    "path": "/",
}

def set_email_cookie(response, email: str) -> None:
    """
    Set a short-lived, readable cookie with the user's email.
    Used only for UX on the verify page.
    """
    response.set_cookie(
        EMAIL_COOKIE_NAME,
        str(email),
        **EMAIL_COOKIE_SETTINGS,
    )

def clear_email_cookie(response) -> None:
    """
    Clear the pending email cookie after verification.
    """
    response.delete_cookie(
        EMAIL_COOKIE_NAME,
        path=EMAIL_COOKIE_SETTINGS["path"],
    )
