# apps/accounts/auth_strategies/facebook.py
from __future__ import annotations

import logging

import requests
from django.conf import settings

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError
from .base import BaseAuthStrategy, SocialUserData
from .registry import auth_strategy_registry

logger = logging.getLogger("apps.accounts")

FACEBOOK_DEBUG_TOKEN_URL = "https://graph.facebook.com/debug_token"
FACEBOOK_USER_INFO_URL   = "https://graph.facebook.com/me"
FACEBOOK_USER_FIELDS     = "id,name,email,picture.type(large)"


class FacebookAuthStrategy(BaseAuthStrategy):
    """
    Authenticate via Facebook user access token.

    Frontend flow:
        1. User clicks "Continue with Facebook"
        2. Facebook Login dialog shown
        3. Frontend receives Facebook user access token
        4. Frontend sends token to POST /api/accounts/auth/social/
        5. We verify token via Facebook debug_token endpoint
        6. We fetch user profile from Graph API
        7. We normalize to SocialUserData

    Two-step process (unlike Google one-step):
        Step 1: debug_token — verify token is valid and for our app
        Step 2: /me — fetch actual user data with verified token

    Why two steps:
        Facebook access tokens carry no user data themselves.
        Google ID tokens (JWT) embed user data in the token body.
        Facebook requires a separate Graph API call to get user data.

    Email note:
        Facebook does NOT guarantee email is returned.
        Users can decline email permission or use phone-only accounts.
        We handle missing email with a DomainError — email is required
        for our User model (unique identifier).
    """

    def authenticate(self, token: str) -> SocialUserData:
        self._verify_token(token)
        profile = self._fetch_user_profile(token)
        return self._normalize(profile)

    def _verify_token(self, token: str) -> None:
        """
        Verify token with Facebook debug_token endpoint.

        Uses app_id|app_secret as the input_token for server-side call.
        This is the secure verification method — never trust client-side only.

        Raises:
            DomainError: Network failure, invalid token, wrong app.
        """
        app_token = f"{settings.FACEBOOK_APP_ID}|{settings.FACEBOOK_APP_SECRET}"

        try:
            response = requests.get(
                FACEBOOK_DEBUG_TOKEN_URL,
                params={
                    "input_token":  token,
                    "access_token": app_token,
                },
                timeout=10,
            )
        except requests.Timeout:
            logger.warning("Facebook debug_token timeout")
            raise DomainError(
                "Facebook authentication timed out. Please try again.",
                code=ErrorCode.AUTH_PROVIDER_UNREACHABLE,
                status_code=400,
            )
        except requests.RequestException:
            logger.exception("Facebook debug_token network failure")
            raise DomainError(
                "Unable to reach Facebook. Please try again.",
                code=ErrorCode.AUTH_PROVIDER_UNREACHABLE,
                status_code=400,
            )

        if response.status_code != 200:
            raise DomainError(
                "Invalid or expired Facebook token.",
                code=ErrorCode.INVALID_SOCIAL_TOKEN,
                status_code=400,
            )

        data = response.json().get("data", {})

        # Token must be valid
        if not data.get("is_valid"):
            logger.warning(
                "Facebook token is_valid=False: %s",
                response.json(),
            )
            raise DomainError(
                "Invalid or expired Facebook token.",
                code=ErrorCode.INVALID_SOCIAL_TOKEN,
                status_code=400,
            )

        # Token must belong to OUR app
        if str(data.get("app_id")) != str(settings.FACEBOOK_APP_ID):
            logger.warning(
                "Facebook token app_id mismatch: got=%s expected=%s",
                data.get("app_id"),
                settings.FACEBOOK_APP_ID,
            )
            raise DomainError(
                "Facebook token was not issued for this application.",
                code=ErrorCode.INVALID_SOCIAL_TOKEN,
                status_code=400,
            )

    def _fetch_user_profile(self, token: str) -> dict:
        """
        Fetch user profile from Facebook Graph API.

        Raises:
            DomainError: Network failure or API error.
        """
        try:
            response = requests.get(
                FACEBOOK_USER_INFO_URL,
                params={
                    "fields":       FACEBOOK_USER_FIELDS,
                    "access_token": token,
                },
                timeout=10,
            )
        except requests.RequestException:
            logger.exception("Facebook Graph API network failure")
            raise DomainError(
                "Unable to fetch your Facebook profile. Please try again.",
                code=ErrorCode.AUTH_PROVIDER_UNREACHABLE,
                status_code=400,
            )

        if response.status_code != 200:
            raise DomainError(
                "Failed to retrieve Facebook profile.",
                code=ErrorCode.INVALID_SOCIAL_TOKEN,
                status_code=400,
            )

        return response.json()

    def _normalize(self, profile: dict) -> SocialUserData:
        """
        Normalize Facebook profile into SocialUserData.

        Raises:
            DomainError: Email not provided — required for our system.
        """
        email = profile.get("email", "").lower().strip()

        if not email:
            raise DomainError(
                "Your Facebook account did not provide an email address. "
                "Please ensure email permission is granted, or register "
                "using email and password instead.",
                code=ErrorCode.SOCIAL_EMAIL_MISSING,
                status_code=400,
            )

        avatar_url = ""
        if picture := profile.get("picture", {}).get("data", {}).get("url"):
            avatar_url = picture

        return SocialUserData(
            provider_id  = str(profile["id"]),
            provider     = "facebook",
            email        = email,
            full_name    = profile.get("name", "").strip() or email.split("@")[0],
            avatar_url   = avatar_url,
            access_token = "",
            is_verified  = True,
            is_provider_email_verified = True,  
            extra_data                = profile, 
        )


# ── Self-registration ──────────────────────────────────────────────────────────
auth_strategy_registry.register("facebook", FacebookAuthStrategy)