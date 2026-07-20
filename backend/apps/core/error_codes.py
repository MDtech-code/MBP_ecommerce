# apps/core/error_codes.py
from __future__ import annotations


class ErrorCode:
    """
    Centralized registry of all machine-readable error codes.

    Rules:
        - Every custom error raised ANYWHERE in the project
          must use a code defined here. No string literals at raise sites.
        - Names are SCREAMING_SNAKE_CASE constants.
        - Values are snake_case strings — these go to the frontend as-is.
        - Group codes by domain with a comment block.
        - Never delete a code — deprecate it with a comment instead.
        - Frontend switches on these values, so treat them as a public API.
          Changing a value is a breaking change.

    Usage (backend):
        from apps.core.error_codes import ErrorCode

        raise serializers.ValidationError(
            detail=_("An account with this email already exists."),
            code=ErrorCode.EMAIL_ALREADY_EXISTS,
        )

    Usage (frontend):
        if (errors?.non_fields?.code === ErrorCode.EMAIL_NOT_VERIFIED) {
            // show resend button
        }
    """

    # ── Authentication ────────────────────────────────────────────────────────
    INVALID_CREDENTIALS     = "invalid_credentials"
    EMAIL_NOT_VERIFIED      = "email_not_verified"
    ACCOUNT_DISABLED        = "account_disabled"
    ACCOUNT_INACTIVE        = "account_inactive"
    SESSION_EXPIRED         = "session_expired"
    TOKEN_INVALID           = "token_invalid"
    TOKEN_EXPIRED           = "token_expired"
    
    
    # ── OTP ───────────────────────────────────────────────────────────────────
    OTP_RESEND_COOLDOWN          = "otp_resend_cooldown"
    OTP_NOT_FOUND                = "otp_not_found"
    OTP_EXPIRED                  = "otp_expired"
    OTP_INVALID                  = "otp_invalid"
    OTP_ATTEMPTS_EXCEEDED        = "otp_attempts_exceeded"

    # ── Verified Session ──────────────────────────────────────────────────────
    VERIFICATION_SESSION_INVALID = "verification_session_invalid"
    VERIFICATION_SESSION_EXPIRED = "verification_session_expired"

    # ── Social Auth ───────────────────────────────────────────────────────────
    UNSUPPORTED_AUTH_PROVIDER    = "unsupported_auth_provider"
    INVALID_SOCIAL_TOKEN         = "invalid_social_token"
    AUTH_PROVIDER_UNREACHABLE    = "auth_provider_unreachable"
    SOCIAL_EMAIL_NOT_VERIFIED    = "social_email_not_verified"
    SOCIAL_EMAIL_MISSING         = "social_email_missing"
    ACCOUNT_INACTIVE             = "account_inactive"
    

    # ── Registration / Email ──────────────────────────────────────────────────
    EMAIL_ALREADY_EXISTS    = "email_already_exists"
    EMAIL_INVALID_FORMAT    = "email_invalid_format"

    # ── User / Profile ────────────────────────────────────────────────────────
    INVALID_FULL_NAME       = "invalid_full_name"
    INVALID_PHONE           = "invalid_phone"
    INVALID_DATE_OF_BIRTH   = "invalid_date_of_birth"
    INVALID_ADDRESS         = "invalid_address"

    # ── Password ──────────────────────────────────────────────────────────────
    PASSWORD_TOO_WEAK       = "password_too_weak"
    PASSWORD_MISMATCH       = "password_mismatch"
    PASSWORD_SAME_AS_OLD    = "password_same_as_old"

    # ── File Upload ───────────────────────────────────────────────────────────
    INVALID_IMAGE_SIZE      = "invalid_image_size"
    INVALID_IMAGE_TYPE      = "invalid_image_type"

    # ── Top-level category codes (go into errors.code) ───────────────────────
    # These describe WHAT KIND of error occurred, not the specific cause.
    # Used by exceptions.py to populate the top-level errors.code field.
    # Frontend branches on these to decide how to handle the error class,
    # then reads non_fields.code for the specific cause.
    VALIDATION_ERROR        = "validation_error"
    AUTHENTICATION_ERROR    = "authentication_error"
    PERMISSION_ERROR        = "permission_error"
    NOT_FOUND               = "not_found"
    RATE_LIMIT_EXCEEDED     = "rate_limit_exceeded"
    SERVER_ERROR            = "server_error"
    METHOD_NOT_ALLOWED      = "method_not_allowed"
    CONFLICT_ERROR          = "conflict_error"      # 409 — valid state, operation refused
