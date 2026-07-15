# apps/accounts/exceptions.py
"""
Account-domain exception hierarchy.

Why custom exceptions instead of raising serializers.ValidationError
directly from services:

    1. Services must not import DRF — services are framework-agnostic.
       They are pure Python business logic. Today DRF, tomorrow GraphQL
       or a CLI command — services should not care.

    2. Views catch domain exceptions and convert them to HTTP responses.
       This is the view's job, not the service's job.

    3. Custom exceptions carry structured data (field name, error code)
       so the view can build a precise error response without string parsing.

    4. Domain exceptions are testable without an HTTP request context.
       `pytest.raises(EmailAlreadyExistsError)` is clear and explicit.

Hierarchy:
    AccountError               ← base for all account domain errors
        RegistrationError      ← base for registration failures
            EmailAlreadyExistsError
            WeakPasswordError
        AuthenticationError    ← base for login failures
            InvalidCredentialsError
            EmailNotVerifiedError
            AccountDisabledError
        TokenError             ← base for token failures
            TokenInvalidError
            TokenExpiredError
"""
from __future__ import annotations

from apps.core.error_codes import ErrorCode


class AccountError(Exception):
    """
    Base for all account domain exceptions.

    Every account exception carries:
        message   : human-readable description (may be shown to user)
        code      : machine-readable code from ErrorCode registry
        field     : which field caused the error (None = non-field error)

    Views inspect these three attributes to build the standardized
    error envelope without any string parsing or isinstance chains.
    """
    default_message: str = "An account error occurred."
    default_code: str = ErrorCode.SERVER_ERROR
    default_field: str | None = None

    def __init__(
        self,
        message: str | None = None,
        code: str | None = None,
        field: str | None = None,
    ) -> None:
        self.message = message or self.default_message
        self.code = code or self.default_code
        self.field = field or self.default_field
        super().__init__(self.message)

    def to_error_dict(self) -> dict:
        """
        Convert to the shape expected by BaseAPIView.error_response(errors=...).

        Returns field-keyed dict if field is set, otherwise non_field_errors shape.
        This is then passed directly to _format_errors() in the view.
        """
        if self.field:
            return {self.field: [{"message": self.message, "code": self.code}]}
        return {"non_field_errors": [{"message": self.message, "code": self.code}]}


# ── Registration Errors ───────────────────────────────────────────────────────

class RegistrationError(AccountError):
    """Base for all registration-phase failures."""
    default_message = "Registration failed."
    default_code = ErrorCode.VALIDATION_ERROR


class EmailAlreadyExistsError(RegistrationError):
    """
    Raised when email uniqueness check fails inside a transaction.

    Why not rely on IntegrityError from DB:
        DB IntegrityError is a last resort. We check explicitly first
        so we can raise a clean domain error with the correct field name
        and error code. IntegrityError is still caught as a fallback
        for the race condition window.
    """
    default_message = "An account with this email already exists."
    default_code = ErrorCode.EMAIL_ALREADY_EXISTS
    default_field = "email"


class WeakPasswordError(RegistrationError):
    default_message = "Password does not meet security requirements."
    default_code = ErrorCode.PASSWORD_TOO_WEAK
    default_field = "password"


# ── Authentication Errors ─────────────────────────────────────────────────────

class AuthenticationError(AccountError):
    """Base for all authentication-phase failures."""
    default_message = "Authentication failed."
    default_code = ErrorCode.AUTHENTICATION_ERROR


class InvalidCredentialsError(AuthenticationError):
    """
    Raised when email/password combination does not match.

    Security note: message is intentionally vague — we never reveal
    whether the email exists or the password was wrong. This prevents
    user enumeration attacks.
    """
    default_message = "Invalid email or password."
    default_code = ErrorCode.INVALID_CREDENTIALS


class EmailNotVerifiedError(AuthenticationError):
    default_message = "Please verify your email address before logging in."
    default_code = ErrorCode.EMAIL_NOT_VERIFIED


class AccountDisabledError(AuthenticationError):
    default_message = "Your account has been disabled. Please contact support."
    default_code = ErrorCode.ACCOUNT_DISABLED


# ── Token Errors ──────────────────────────────────────────────────────────────

class TokenError(AccountError):
    """Base for token-related failures."""
    default_message = "Token error."
    default_code = ErrorCode.TOKEN_INVALID


class TokenInvalidError(TokenError):
    default_message = "This verification link is invalid."
    default_code = ErrorCode.TOKEN_INVALID


class TokenExpiredError(TokenError):
    default_message = "This verification link has expired. Please request a new one."
    default_code = ErrorCode.TOKEN_EXPIRED