# apps/accounts/auth_strategies/facebook.py
from __future__ import annotations

import logging

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

    def authenticate(self, token: str) -> SocialUserData:
        self._verify_token(token)
        profile = self._fetch_user_profile(token)
        return self._normalize(profile)

    def _verify_token(self, token: str) -> None:
        app_token = f"{settings.FACEBOOK_APP_ID}|{settings.FACEBOOK_APP_SECRET}"

        
        payload = self._get(
            FACEBOOK_DEBUG_TOKEN_URL,
            params={"input_token": token, "access_token": app_token},
            provider="Facebook",
            unreachable_message="Facebook authentication timed out. Please try again.",
            invalid_status_message="Invalid or expired Facebook token.",
        )

        data = payload.get("data", {})

        # Token must be valid
        if not data.get("is_valid"):
            logger.warning("Facebook token is_valid=False: %s", payload)
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

        return self._get(
            FACEBOOK_USER_INFO_URL,
            params={"fields": FACEBOOK_USER_FIELDS, "access_token": token},
            provider="Facebook",
            unreachable_message="Unable to fetch your Facebook profile. Please try again.",
            invalid_status_message="Failed to retrieve Facebook profile.",
        )

    def _normalize(self, profile: dict) -> SocialUserData:
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


auth_strategy_registry.register("facebook", FacebookAuthStrategy)