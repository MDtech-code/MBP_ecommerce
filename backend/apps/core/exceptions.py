"""
apps/core/exceptions.py
────────────────────────
Domain-level exception hierarchy. Framework-agnostic by design.

This module must never import Django, DRF, or anything under apps.core.api.
That constraint is what lets this file be copied into a non-Django project
unchanged. Everything an HTTP layer needs to turn one of these exceptions
into a response is available on the exception instance itself, via
to_envelope() — no external file has to know the difference between a
DomainError and an InfrastructureError to handle either one correctly.

Each exception carries enough self-description (status_code, category,
default_code, notify) that a caller holding a bare BaseAppError reference
can treat any subclass uniformly, without isinstance checks. New exception
types are added here, and only here — nothing outside this file needs to
change for a new subclass to work end-to-end.
"""

from __future__ import annotations

from typing import Any


class BaseAppError(Exception):
    """
    Holds the fields every subclass needs regardless of category:
    a human-readable message, a machine-readable code, an HTTP status,
    optional data safe to expose to a client, and optional data .

    Class attributes act as defaults that subclasses override:
        status_code   - HTTP status this exception maps to
        category      - grouping label used by the HTTP layer for logging
                         and response shaping ("domain", "system", etc.)
        default_code  - machine-readable code used when the caller does
                         not supply one explicitly
        default_notify - whether this exception should alert monitoring
                         (e.g. Sentry, PagerDuty) by default

    """

    status_code: int = 500
    category: str = "unexpected"
    default_code: str = "app_error"
    default_notify: bool = False

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        client_extra: dict[str, Any] | None = None,
        internal: dict[str, Any] | None = None,
        notify: bool | None = None,
    ) -> None:
        """
        Args:
            message: Human-readable description of what went wrong.
            code: Machine-readable error code. Falls back to the subclass's default_code if not supplied.
            client_extra: Structured data safe to serialize into an HTTP response body.
            internal: Structured data for logging/debugging only.
            notify: Overrides the subclass's default_notify for this specific instance.
        """
        super().__init__(message)
        self.message = message
        self.code = code or self.default_code
        self.client_extra = client_extra
        self.internal = internal
        self.notify = self.default_notify if notify is None else notify

    def to_envelope(self) -> dict[str, Any]:
        """
        Returns exactly the fields an HTTP layer needs to construct the
        non_fields portion of an error response: category, message,
        code, and extra (client-safe data only). 
        """
        return {
            "category": self.category,
            "message": self.message,
            "code": self.code,
            "extra": self.client_extra,
        }


class DomainError(BaseAppError):
    """
    A 4xx-class error caused by client input or client-visible state.
    Examples: invalid input the serializer layer didn't already catch,
    a business rule violation, a resource conflict. 
    """

    category = "domain"
    default_code = "domain_error"
    default_notify = False

    ALLOWED_STATUS_CODES = {400, 401, 403, 404, 409, 422}

    def __init__(
        self,
        message: str,
        *,
        code: str = "domain_error",
        status_code: int = 400,
        client_extra: dict[str, Any] | None = None,
        internal: dict[str, Any] | None = None,
    ) -> None:
        """
        Args:
            message: Human-readable description of the violated rule.
            code: Machine-readable error code identifying the specific domain rule that failed.
            status_code: HTTP status for this error. Must be a member of ALLOWED_STATUS_CODES.
            client_extra: Structured data safe to return to the client.
            internal: Structured data for logging only.

        Raises:
            ValueError: If status_code is not in ALLOWED_STATUS_CODES.
                For 5xx conditions, raise InfrastructureError instead —
                a DomainError is never allowed to represent a server
                defect.
        """
        if status_code not in self.ALLOWED_STATUS_CODES:
            raise ValueError(
                f"DomainError status_code must be one of "
                f"{sorted(self.ALLOWED_STATUS_CODES)}, got {status_code}. "
                f"For 5xx conditions use InfrastructureError instead."
            )
        super().__init__(message, code=code, client_extra=client_extra, internal=internal)
        self.status_code = status_code


class NotFoundError(DomainError):
    """A requested resource does not exist or is not visible to the caller."""

    default_code = "not_found"

    def __init__(
        self,
        message: str = "The requested resource was not found.",
        *,
        code: str = "not_found",
        client_extra: dict[str, Any] | None = None,
        internal: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            status_code=404,
            client_extra=client_extra,
            internal=internal,
        )


class AuthenticationRequiredError(DomainError):
    """The request has no valid credentials attached."""

    default_code = "authentication_error"

    def __init__(
        self,
        message: str = "Authentication required.",
        *,
        code: str = "authentication_error",
        client_extra: dict[str, Any] | None = None,
        internal: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            status_code=401,
            client_extra=client_extra,
            internal=internal,
        )


class PermissionDeniedError(DomainError):
    """The request has valid credentials but insufficient access."""

    default_code = "permission_error"

    def __init__(
        self,
        message: str = "You do not have permission to perform this action.",
        *,
        code: str = "permission_error",
        client_extra: dict[str, Any] | None = None,
        internal: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            message,
            code=code,
            status_code=403,
            client_extra=client_extra,
            internal=internal,
        )


class InfrastructureError(BaseAppError):
    """
    A 5xx-class error caused by a system or dependency failure.

    Examples: database unreachable, third-party API timeout, message
    queue unavailable. status_code is a class attribute here, not an
    instance attribute — every InfrastructureError is 503, there is no
    per-instance variation to support, unlike DomainError.

    notify defaults to True at the class level because an infrastructure
    failure is, by default, assumed to be an unexpected defect worth
    paging on-call about. Pass notify=False at the call site for a
    specific instance that represents an already-handled, expected
    outage (e.g. a retried request to a dependency known to be degraded)
    so it logs as a warning instead of alerting.
    """

    status_code = 503
    category = "system"
    default_code = "infrastructure_error"
    default_notify = True

    def __init__(
        self,
        message: str,
        *,
        code: str = "infrastructure_error",
        notify: bool = True,
        client_extra: dict[str, Any] | None = None,
        internal: dict[str, Any] | None = None,
    ) -> None:
        """
        Construct an InfrastructureError.

        Args:
            message: Human-readable description of the failure.
            code: Machine-readable error code identifying the failure.
            notify: Whether this specific instance should alert
                monitoring. Defaults to True; pass False for a known,
                already-handled outage that does not need to page anyone.
            client_extra: Structured data safe to return to the client.
            internal: Structured data for logging only.
        """
        super().__init__(
            message,
            code=code,
            client_extra=client_extra,
            internal=internal,
            notify=notify,
        )