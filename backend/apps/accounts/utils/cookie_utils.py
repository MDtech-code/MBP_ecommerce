# apps/accounts/utils/cookie_utils.py
from __future__ import annotations



# ── Cookie configuration ───────────────────────────────────────────────────────


REFRESH_COOKIE_NAME = "refresh_token"

COOKIE_SETTINGS = {
    "httponly": True,
    "secure":True,
    "samesite": "Lax",
    "max_age": 7 * 24 * 60 * 60,  
    "path": "/api/accounts/",
}


def set_refresh_cookie(response, refresh_token: str) -> None:
    
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        str(refresh_token),
        **COOKIE_SETTINGS,
    )


def clear_refresh_cookie(response) -> None:
    
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
    
    response.set_cookie(
        EMAIL_COOKIE_NAME,
        str(email),
        **EMAIL_COOKIE_SETTINGS,
    )

def clear_email_cookie(response) -> None:
    
    response.delete_cookie(
        EMAIL_COOKIE_NAME,
        path=EMAIL_COOKIE_SETTINGS["path"],
    )
