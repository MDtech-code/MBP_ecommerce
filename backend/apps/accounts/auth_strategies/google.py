# apps/accounts/auth_strategies/google.py
from __future__ import annotations

import logging

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError
from .base import BaseAuthStrategy, SocialUserData
from .registry import auth_strategy_registry

logger = logging.getLogger("apps.accounts")


GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class GoogleAuthStrategy(BaseAuthStrategy):

    def authenticate(self, token: str) -> SocialUserData:
        payload = self._verify_with_google(token)
        self._assert_email_verified(payload)
        return self._normalize(payload)

    def _verify_with_google(self, token: str) -> dict:
       
        return self._get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {token}"},
            provider="Google",
            unreachable_message="Google authentication timed out. Please try again.",
            invalid_status_message="Invalid or expired Google token.",
        )

    def _assert_email_verified(self, payload: dict) -> None:
        if not payload.get("email_verified"):
            raise DomainError(
                "Your Google account email is not verified. "
                "Please verify your Google email and try again.",
                code=ErrorCode.SOCIAL_EMAIL_NOT_VERIFIED,
                status_code=400,
            )

    def _normalize(self, payload: dict) -> SocialUserData:
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
            token_expires_at           = None,
            is_verified                = True,
            is_provider_email_verified = bool(payload.get("email_verified")),
            extra_data                 = payload,
        )


auth_strategy_registry.register("google", GoogleAuthStrategy)
# # apps/accounts/auth_strategies/google.py
# from __future__ import annotations

# import logging


# import requests


# from apps.core.error_codes import ErrorCode
# from apps.core.exceptions import DomainError
# from .base import BaseAuthStrategy, SocialUserData
# from .registry import auth_strategy_registry

# logger = logging.getLogger("apps.accounts")


# GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


# class GoogleAuthStrategy(BaseAuthStrategy):
    
#     def authenticate(self, token: str) -> SocialUserData:
#         payload = self._verify_with_google(token)
#         self._assert_email_verified(payload)
#         return self._normalize(payload)

#     def _verify_with_google(self, token: str) -> dict:
        
#         try:
#             response = requests.get(
#                 GOOGLE_USERINFO_URL,
#                 headers={"Authorization": f"Bearer {token}"},
#                 timeout=10,
#             )
#         except requests.Timeout:
#             logger.warning("Google userinfo timeout")
#             raise DomainError(
#                 "Google authentication timed out. Please try again.",
#                 code=ErrorCode.AUTH_PROVIDER_UNREACHABLE,
#                 status_code=400,
#             )
#         except requests.RequestException:
#             logger.exception("Google userinfo network failure")
#             raise DomainError(
#                 "Unable to reach Google. Please try again.",
#                 code=ErrorCode.AUTH_PROVIDER_UNREACHABLE,
#                 status_code=400,
#             )

#         if response.status_code != 200:
#             logger.warning(
#                 "Google userinfo rejected token: status=%s body=%s",
#                 response.status_code,
#                 response.text[:200],
#             )
#             raise DomainError(
#                 "Invalid or expired Google token.",
#                 code=ErrorCode.INVALID_SOCIAL_TOKEN,
#                 status_code=400,
#             )

#         return response.json()

#     def _assert_email_verified(self, payload: dict) -> None:
       
#         if not payload.get("email_verified"):
#             raise DomainError(
#                 "Your Google account email is not verified. "
#                 "Please verify your Google email and try again.",
#                 code=ErrorCode.SOCIAL_EMAIL_NOT_VERIFIED,
#                 status_code=400,
#             )

#     def _normalize(self, payload: dict) -> SocialUserData:
        
#         first     = payload.get("given_name", "")
#         last      = payload.get("family_name", "")
#         full_name = f"{first} {last}".strip()

#         if not full_name:
#             full_name = (
#                 payload.get("email", "")
#                 .split("@")[0]
#                 .replace(".", " ")
#                 .title()
#             )

#         return SocialUserData(
#             provider_id                = payload["sub"],
#             provider                   = "google",
#             email                      = payload["email"].lower().strip(),
#             full_name                  = full_name,
#             avatar_url                 = payload.get("picture", ""),
#             access_token               = "",
#             refresh_token              = "",
#             token_expires_at           = None,
#             is_verified                = True,
#             is_provider_email_verified = bool(payload.get("email_verified")),
#             extra_data                 = payload,
#         )


# auth_strategy_registry.register("google", GoogleAuthStrategy)
