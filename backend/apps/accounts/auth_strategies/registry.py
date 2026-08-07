# apps/accounts/auth_strategies/registry.py
from __future__ import annotations

import logging

from apps.core.exceptions import DomainError
from apps.core.error_codes import ErrorCode
from .base import BaseAuthStrategy

logger = logging.getLogger("apps.accounts")


class AuthStrategyRegistry:
    def __init__(self) -> None:
        self._strategies: dict[str, type[BaseAuthStrategy]] = {}

    def register(
        self,
        provider: str,
        strategy_class: type[BaseAuthStrategy],
    ) -> None:
        
        slug = provider.lower()
        self._strategies[slug] = strategy_class
        logger.debug("Auth strategy registered: provider=%s", slug)

    def get(self, provider: str) -> BaseAuthStrategy:
        
        strategy_class = self._strategies.get(provider.lower())

        if not strategy_class:
            raise DomainError(
                f"'{provider}' is not a supported authentication provider.",
                code=ErrorCode.UNSUPPORTED_AUTH_PROVIDER,
                status_code=400,
            )

        return strategy_class()

    @property
    def supported_providers(self) -> list[str]:
        
        return list(self._strategies.keys())


# ── Singleton ──────────────────────────────────────────────────────────────────
auth_strategy_registry = AuthStrategyRegistry()