# apps/accounts/auth_strategies/base.py
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SocialUserData:
    """
    Provider-agnostic normalized user data.

    Every strategy MUST populate all required fields.
    Optional fields default to safe empty values.

    Fields:
        provider_id:      Unique ID from provider. Never changes.
        provider:         Slug matching SocialProvider choices.
        email:            Verified email. Already lowercased by strategy.
        full_name:        Constructed by strategy from provider parts.
        avatar_url:       Profile picture. Empty string if not provided.
        access_token:     Provider access token for API calls.
        refresh_token:    Provider refresh token. Empty if not issued.
        token_expires_at: Token expiry. None if provider does not specify.
        is_verified:      Provider confirmed this email. Almost always True.
    """
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
    """
    Contract every authentication strategy must fulfill.

    Subclasses implement authenticate() only.
    All provider-specific logic stays inside the subclass.
    Service layer only ever sees SocialUserData.
    """

    @abstractmethod
    def authenticate(self, token: str) -> SocialUserData:
        """
        Verify token with provider. Return normalized user data.

        Args:
            token: Raw token from client (ID token or access token).

        Returns:
            SocialUserData — normalized, provider-agnostic.

        Raises:
            DomainError: Token invalid, expired, wrong audience,
                         provider unreachable.
        """
        ...