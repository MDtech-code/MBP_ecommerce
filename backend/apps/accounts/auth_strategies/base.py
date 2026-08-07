# apps/accounts/auth_strategies/base.py
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import requests

from apps.core.error_codes import ErrorCode
from apps.core.exceptions import DomainError

logger = logging.getLogger("apps.accounts")


@dataclass
class SocialUserData:
    provider_id:      str
    provider:         str
    email:            str
    full_name:        str
    avatar_url:       str       = ""
    access_token:     str       = ""
    refresh_token:    str       = ""
    token_expires_at: object    = None
    is_verified:      bool      = True
    is_provider_email_verified: bool     = False
    extra_data:                dict      = field(default_factory=dict)


class BaseAuthStrategy(ABC):
    def _get(
        self,
        url: str,
        *,
        params: dict | None = None,
        headers: dict | None = None,
        timeout: int = 10,
        provider: str,
        unreachable_message: str,
        invalid_status_message: str,
        invalid_status_code_error: str = ErrorCode.INVALID_SOCIAL_TOKEN,
    ) -> dict:
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
        except requests.Timeout:
            logger.warning("%s request timeout: url=%s", provider, url)
            raise DomainError(
                unreachable_message,
                code=ErrorCode.AUTH_PROVIDER_UNREACHABLE,
                status_code=400,
            )
        except requests.RequestException:
            logger.exception("%s network failure: url=%s", provider, url)
            raise DomainError(
                unreachable_message,
                code=ErrorCode.AUTH_PROVIDER_UNREACHABLE,
                status_code=400,
            )

        if response.status_code != 200:
            logger.warning(
                "%s rejected request: status=%s body=%s",
                provider,
                response.status_code,
                response.text[:200],
            )
            raise DomainError(
                invalid_status_message,
                code=invalid_status_code_error,
                status_code=400,
            )

        return response.json()

    @abstractmethod
    def authenticate(self, token: str) -> SocialUserData:
        pass
