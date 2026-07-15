"""
apps/core/exceptions.py
───────────────────────
Transport-agnostic exception hierarchy for the entire project.

DEPENDENCY RULE
───────────────
This module has ZERO imports from apps.core.api, DRF, or Django HTTP.
It is safe to import from any layer:

    Domain / Service layer  →  raises these
    API layer               →  catches these, maps to HTTP responses
    Celery tasks            →  catches these, decides whether to retry
    Management commands     →  catches these, formats CLI output

Layer import direction (must never be reversed):

    core.exceptions  ←  core.api.exceptions
    core.exceptions  ←  services.*
    core.exceptions  ←  tasks.*

Exception hierarchy
───────────────────
    BaseAppError
    ├── DomainError          Business-rule / invariant violation (4xx)
    └── InfrastructureError  Recoverable infrastructure failure (503)

INTENT: BaseAppError is never raised directly — only its subclasses.
It exists to give catch-all handlers a single type to catch and to
guarantee that status_code is always accessible through the base type
without AttributeError.
"""

from __future__ import annotations

from typing import Any


# ─── Base ─────────────────────────────────────────────────────────────────────

class BaseAppError(Exception):
    """
    Root for all application-defined exceptions.

    Never raise this directly — raise DomainError or InfrastructureError.
    It exists so catch-all handlers can do:

        except BaseAppError as exc:
            log(exc.status_code)   # always safe — never AttributeError

    Shared contract:
        message      – human-readable, safe to show end-users
        code         – machine-readable slug for programmatic handling
        status_code  – HTTP status; 0 here, overridden by every subclass
        client_extra – structured data the client needs to act on
        internal     – diagnostic data; NEVER forwarded to the client,
                       only written to logs / Sentry
    """

    #: Sentinel — subclasses always override this with a real HTTP status.
    #: Declared here so `exc.status_code` never raises AttributeError when
    #: catching through the base type.
    status_code: int = 0

    def __init__(
        self,
        message: str,
        *,
        code: str,
        client_extra: dict[str, Any] | None = None,
        internal: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.client_extra = client_extra  # serialized into response
        self.internal = internal          # logged / sent to Sentry, never to client


# ─── DomainError ──────────────────────────────────────────────────────────────

class DomainError(BaseAppError):
    """
    Intentional business-rule / domain-invariant violation.

    Raise when application logic determines the requested operation is
    not allowed given the current state of the domain — not because the
    request is malformed, but because the domain says no.

    HTTP mapping (decided by the API handler, not this class):
        status_code=400  Generic domain rejection / bad request  (default)
        status_code=409  Conflict — current state prevents the operation

    Why only 400 and 409?
        These two cover every real domain error scenario we have today.
        Other 4xx codes (410, 422, etc.) require concrete use cases before
        being added — ALLOWED_STATUS_CODES is a public contract that every
        developer reads as "valid choices."

    Args:
        message:      Human-readable explanation shown to the user.
        code:         Machine-readable slug (e.g. "cart_empty").
        status_code:  HTTP status the API handler should return.
                      Must be a member of ALLOWED_STATUS_CODES.
                      Defaults to 400; use 409 for state-conflict situations.
        client_extra: Structured data safe to forward to the client.
                      Example: {"applied_on": "2024-01-15"}
        internal:     Diagnostic data for logs / Sentry only.
                      Example: {"cart_id": 42, "user_id": 7}
                      NEVER reaches the client response.

    Examples::

        # Generic domain rejection → 400
        raise DomainError(
            "Your cart is empty. Add items before checking out.",
            code="cart_empty",
        )

        # State conflict → 409
        raise DomainError(
            "This order has already been cancelled.",
            code="order_already_cancelled",
            status_code=409,
        )

        # Conflict with client-safe context
        raise DomainError(
            "Coupon has already been used.",
            code="coupon_already_used",
            status_code=409,
            client_extra={"applied_on": "2024-01-15"},
            internal={"coupon_id": 99, "used_by_user_id": 12},
        )
    """

    #: Only these HTTP status codes are valid for domain errors.
    #: Add new codes here only when a concrete use case exists —
    #: this set is a public contract read by every developer on the team.
    ALLOWED_STATUS_CODES: frozenset[int] = frozenset({400, 409})

    def __init__(
        self,
        message: str,
        *,
        code: str = "domain_error",
        status_code: int = 400,
        client_extra: dict[str, Any] | None = None,
        internal: dict[str, Any] | None = None,
    ) -> None:
        if status_code not in self.ALLOWED_STATUS_CODES:
            raise ValueError(
                f"DomainError status_code must be one of "
                f"{sorted(self.ALLOWED_STATUS_CODES)}, got {status_code}. "
                f"For 5xx conditions use InfrastructureError instead."
            )
        super().__init__(
            message,
            code=code,
            client_extra=client_extra,
            internal=internal,
        )
        self.status_code: int = status_code  # overrides BaseAppError sentinel (0)


# ─── InfrastructureError ──────────────────────────────────────────────────────

class InfrastructureError(BaseAppError):
    """
    Recoverable infrastructure / third-party integration failure.

    Raise when an external system or internal subsystem is temporarily
    unavailable and the client should be told to retry.

    Named InfrastructureError (not SystemError) to avoid shadowing
    Python's built-in SystemError, which the interpreter and C
    extensions raise for internal VM-level failures. Shadowing it
    causes silent, nearly impossible-to-debug failures in third-party
    libraries that catch SystemError internally.

    HTTP mapping: always 503 Service Unavailable — not configurable.
    If you need a different 5xx, raise a DRF APIException directly.

    Args:
        message:      Human-readable explanation shown to the user.
        code:         Machine-readable slug (e.g. "payment_gateway_timeout").
        notify:       Whether to alert monitors (Sentry, PagerDuty).
                      Default True. Pass False for expected, handled outages
                      where a fallback is in place and paging on-call adds noise.
                      Note: notify=False also downgrades the log level from
                      ERROR to WARNING — expected outages should not pollute
                      your error log.
        client_extra: Structured data safe to forward to the client.
                      Example: {"retry_after": 30}
        internal:     Diagnostic data for logs / Sentry only.
                      Example: {"gateway_url": "...", "response_code": 504}
                      NEVER reaches the client response.

    Examples::

        # Unexpected failure — alert on-call
        raise InfrastructureError(
            "Payment gateway is temporarily unavailable. Please retry.",
            code="payment_gateway_timeout",
            client_extra={"retry_after": 30},
            internal={"gateway": "stripe", "http_status": 504},
        )

        # Expected, handled outage — fallback already in place, no paging
        raise InfrastructureError(
            "Recommendations unavailable. Showing defaults.",
            code="recommendation_service_down",
            notify=False,
            internal={"service": "rec-engine", "reason": "circuit_open"},
        )
    """

    #: Always 503 — overrides the BaseAppError sentinel (0).
    status_code: int = 503

    def __init__(
        self,
        message: str,
        *,
        code: str = "infrastructure_error",
        notify: bool = True,
        client_extra: dict[str, Any] | None = None,
        internal: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            client_extra=client_extra,
            internal=internal,
        )
        self.notify = notify
        # status_code is a class attribute (503); no instance override needed.
        # Declared at class level so isinstance checks and class inspection work.