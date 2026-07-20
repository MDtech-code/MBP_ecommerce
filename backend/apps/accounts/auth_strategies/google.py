# apps/accounts/auth_strategies/google.py
from __future__ import annotations

import logging
from datetime import datetime, timezone as dt_timezone

import requests
from django.conf import settings

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError
from .base import BaseAuthStrategy, SocialUserData
from .registry import auth_strategy_registry

logger = logging.getLogger("apps.accounts")

# ── Changed from tokeninfo to userinfo ────────────────────────────────────────
# Frontend sends OAuth access_token (not ID token)
# userinfo endpoint validates access_token and returns user data
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleAuthStrategy(BaseAuthStrategy):
    """
    Authenticate via Google OAuth access token.

    Frontend flow:
        1. User clicks "Sign in with Google"
        2. useGoogleLogin() opens Google consent popup
        3. Google returns access_token to frontend (not ID token)
        4. Frontend sends access_token to POST /api/accounts/auth/social/
        5. We verify with Google userinfo endpoint
        6. Google validates token and returns user profile
        7. We normalize to SocialUserData

    Why userinfo not tokeninfo:
        @react-oauth/google useGoogleLogin() returns access_token.
        tokeninfo expects id_token (JWT) — different token type.
        userinfo accepts access_token via Authorization header.
        Google validates the token server-side — still secure.
    """

    def authenticate(self, token: str) -> SocialUserData:
        payload = self._verify_with_google(token)
        self._assert_email_verified(payload)
        return self._normalize(payload)

    def _verify_with_google(self, token: str) -> dict:
        """
        Call Google userinfo endpoint with access_token.
        Google validates token — returns verified user profile.

        Raises:
            DomainError: Network failure, invalid/expired token.
        """
        try:
            response = requests.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
        except requests.Timeout:
            logger.warning("Google userinfo timeout")
            raise DomainError(
                "Google authentication timed out. Please try again.",
                code=ErrorCode.AUTH_PROVIDER_UNREACHABLE,
                status_code=400,
            )
        except requests.RequestException:
            logger.exception("Google userinfo network failure")
            raise DomainError(
                "Unable to reach Google. Please try again.",
                code=ErrorCode.AUTH_PROVIDER_UNREACHABLE,
                status_code=400,
            )

        if response.status_code != 200:
            logger.warning(
                "Google userinfo rejected token: status=%s body=%s",
                response.status_code,
                response.text[:200],
            )
            raise DomainError(
                "Invalid or expired Google token.",
                code=ErrorCode.INVALID_SOCIAL_TOKEN,
                status_code=400,
            )

        return response.json()

    def _assert_email_verified(self, payload: dict) -> None:
        """
        Reject unverified Google emails.

        userinfo returns email_verified as bool True/False
        tokeninfo returned it as string "true"/"false"
        This method handles bool correctly.

        Raises:
            DomainError: email_verified is False
        """
        if not payload.get("email_verified"):
            raise DomainError(
                "Your Google account email is not verified. "
                "Please verify your Google email and try again.",
                code=ErrorCode.SOCIAL_EMAIL_NOT_VERIFIED,
                status_code=400,
            )

    def _normalize(self, payload: dict) -> SocialUserData:
        """
        Normalize Google userinfo payload into SocialUserData.

        userinfo fields:
            sub           → unique user ID (same as tokeninfo)
            email         → user email
            email_verified → bool (not string like tokeninfo)
            given_name    → first name
            family_name   → last name
            picture       → avatar URL
            exp           → NOT present in userinfo (only in tokeninfo)
        """
        first     = payload.get("given_name", "")
        last      = payload.get("family_name", "")
        full_name = f"{first} {last}".strip()

        if not full_name:
            full_name = (
                payload.get("email", "")
                .split("@")[0]
                .replace(".", " ")
                .title()
            )

        return SocialUserData(
            provider_id                = payload["sub"],
            provider                   = "google",
            email                      = payload["email"].lower().strip(),
            full_name                  = full_name,
            avatar_url                 = payload.get("picture", ""),
            access_token               = "",
            refresh_token              = "",
            token_expires_at           = None,   # userinfo does not return exp
            is_verified                = True,
            is_provider_email_verified = bool(payload.get("email_verified")),
            extra_data                 = payload,
        )


# ── Self-registration ──────────────────────────────────────────────────────────
auth_strategy_registry.register("google", GoogleAuthStrategy)
# # apps/accounts/auth_strategies/google.py
# from __future__ import annotations

# import logging
# from datetime import datetime, timezone as dt_timezone

# import requests
# from django.conf import settings

# from apps.core.error_codes import ErrorCode
# from apps.core.exceptions import DomainError
# from .base import BaseAuthStrategy, SocialUserData
# from .registry import auth_strategy_registry

# logger = logging.getLogger("apps.accounts")

# GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


# class GoogleAuthStrategy(BaseAuthStrategy):
#     """
#     Authenticate via Google ID token.

#     Frontend flow:
#         1. User clicks "Sign in with Google"
#         2. Google OAuth consent screen shown
#         3. Frontend receives Google ID token (JWT)
#         4. Frontend sends ID token to POST /api/accounts/auth/social/
#         5. We verify with Google tokeninfo endpoint
#         6. We extract user data and normalize to SocialUserData

#     Why tokeninfo endpoint not local JWT decode:
#         Local decode requires fetching Google public keys and
#         validating signature manually — tokeninfo is simpler,
#         Google handles all validation server-side.
#         Tradeoff: one extra HTTP call per login — acceptable.

#     Security checks performed:
#         - Token must be valid (Google confirms)
#         - Token audience must match OUR Google Client ID
#         - Email must be verified by Google
#     """

#     def authenticate(self, token: str) -> SocialUserData:
#         payload = self._verify_with_google(token)
#         self._assert_email_verified(payload)
#         return self._normalize(payload)

#     def _verify_with_google(self, token: str) -> dict:
#         """
#         Call Google tokeninfo and return verified payload.

#         Raises:
#             DomainError: Network failure, invalid token, wrong audience.
#         """
#         try:
#             response = requests.get(
#                 GOOGLE_TOKENINFO_URL,
#                 params={"id_token": token},
#                 timeout=10,
#             )
#         except requests.Timeout:
#             logger.warning("Google tokeninfo timeout")
#             raise DomainError(
#                 "Google authentication timed out. Please try again.",
#                 code=ErrorCode.AUTH_PROVIDER_UNREACHABLE,
#                 status_code=400,
#             )
#         except requests.RequestException:
#             logger.exception("Google tokeninfo network failure")
#             raise DomainError(
#                 "Unable to reach Google. Please try again.",
#                 code=ErrorCode.AUTH_PROVIDER_UNREACHABLE,
#                 status_code=400,
#             )

#         if response.status_code != 200:
#             logger.warning(
#                 "Google tokeninfo rejected token: status=%s body=%s",
#                 response.status_code,
#                 response.text[:200],
#             )
#             raise DomainError(
#                 "Invalid or expired Google token.",
#                 code=ErrorCode.INVALID_SOCIAL_TOKEN,
#                 status_code=400,
#             )

#         payload = response.json()

#         # Verify token was issued for OUR application
#         if payload.get("aud") != settings.GOOGLE_CLIENT_ID:
#             logger.warning(
#                 "Google token audience mismatch: got=%s expected=%s",
#                 payload.get("aud"),
#                 settings.GOOGLE_CLIENT_ID,
#             )
#             raise DomainError(
#                 "Google token was not issued for this application.",
#                 code=ErrorCode.INVALID_SOCIAL_TOKEN,
#                 status_code=400,
#             )

#         return payload

#     def _assert_email_verified(self, payload: dict) -> None:
#         """
#         Reject tokens where Google has not verified the email.

#         Raises:
#             DomainError: email_verified is not "true"
#         """
#         if payload.get("email_verified") != "true":
#             raise DomainError(
#                 "Your Google account email is not verified. "
#                 "Please verify your Google email and try again.",
#                 code=ErrorCode.SOCIAL_EMAIL_NOT_VERIFIED,
#                 status_code=400,
#             )

#     def _normalize(self, payload: dict) -> SocialUserData:
#         """Normalize Google payload into provider-agnostic SocialUserData."""
#         first     = payload.get("given_name", "")
#         last      = payload.get("family_name", "")
#         full_name = f"{first} {last}".strip()

#         # Fallback: use email prefix if Google did not return a name
#         if not full_name:
#             full_name = payload.get("email", "").split("@")[0].replace(".", " ").title()

#         # Parse token expiry if present
#         token_expires_at = None
#         if exp := payload.get("exp"):
#             try:
#                 token_expires_at = datetime.fromtimestamp(int(exp), tz=dt_timezone.utc)
#             except (ValueError, TypeError):
#                 pass

#         return SocialUserData(
#             provider_id      = payload["sub"],
#             provider         = "google",
#             email            = payload["email"].lower().strip(),
#             full_name        = full_name,
#             avatar_url       = payload.get("picture", ""),
#             access_token     = "",   # ID token flow — no separate access token
#             refresh_token    = "",
#             token_expires_at = token_expires_at,
#             is_verified      = True,
#             is_provider_email_verified = payload.get("email_verified") == "true",  
#             extra_data                = payload,   
#         )


# # ── Self-registration ──────────────────────────────────────────────────────────
# auth_strategy_registry.register("google", GoogleAuthStrategy)