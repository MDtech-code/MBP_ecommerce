# apps/accounts/auth_strategies/registry.py
from __future__ import annotations

import logging

from apps.core.exceptions import DomainError
from apps.core.error_codes import ErrorCode
from .base import BaseAuthStrategy

logger = logging.getLogger("apps.accounts")


class AuthStrategyRegistry:
    """
    Central registry — maps provider slugs to strategy classes.

    Singleton pattern: one instance imported by everything.
    Strategies self-register at module import time.

    Adding a new provider:
        1. Create strategy file
        2. Add one line: auth_strategy_registry.register("slug", Class)
        3. Import the file in apps/accounts/apps.py ready() method
        4. Done — zero other files touched
    """

    def __init__(self) -> None:
        self._strategies: dict[str, type[BaseAuthStrategy]] = {}

    def register(
        self,
        provider: str,
        strategy_class: type[BaseAuthStrategy],
    ) -> None:
        """
        Register a strategy class under a provider slug.

        Args:
            provider:       Lowercase slug — "google", "facebook"
            strategy_class: Class implementing BaseAuthStrategy
        """
        slug = provider.lower()
        self._strategies[slug] = strategy_class
        logger.debug("Auth strategy registered: provider=%s", slug)

    def get(self, provider: str) -> BaseAuthStrategy:
        """
        Resolve slug → instantiated strategy.

        Raises:
            DomainError 400: Provider not registered.
        """
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
        """Returns list of all registered provider slugs."""
        return list(self._strategies.keys())


# ── Singleton ──────────────────────────────────────────────────────────────────
auth_strategy_registry = AuthStrategyRegistry()