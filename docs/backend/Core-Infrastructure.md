```markdown
# Backend Core Infrastructure Reference
# Production E-Commerce Platform — Django + DRF + Celery + Redis

> **Purpose of this document**
> This file is the complete reference for the core infrastructure layer of this
> Django backend. Any AI model or developer onboarding to this project must read
> this entire document before writing a single line of code. Every pattern,
> convention, and constraint described here is already implemented and in
> production use. Do not invent alternatives. Do not guess. Ask for the actual
> file if you need something not covered here.

---

## Table of Contents

1. Project Overview
2. Technology Stack
3. Application Registry
4. Six-Layer Architecture
5. API Response Envelope — The Contract
6. Exception Hierarchy
7. Global Exception Handler
8. BaseAPIView — All Views Inherit This
9. APIResponseMixin
10. Error Codes Registry
11. Two-Level Cache System
12. Pagination System
13. Serializer Fields and Mixins
14. Permission Classes
15. Middleware
16. Authentication and Token Strategy
17. Logging System
18. Settings Reference
19. Critical Rules — Never Violate
20. How to Add a New Endpoint — Checklist
21. Appendix A — Response Examples by Scenario
22. Appendix B — Import Reference

---

## 1. Project Overview

This is a production-scale e-commerce backend built for the Pakistani market.
It follows Daraz-style patterns: verified purchases, COD (Cash on Delivery)
handling, local courier integrations (PostEx, TCS, Leopards), and RTO
(Return to Origin) tracking.

Total Apps: 19 (3 core/infrastructure + 16 domain)
Total Domain Models: 29+

The backend is a REST API consumed by a React frontend. All testing is done
via Postman. The architecture enforces strict consistency — every endpoint
returns the identical envelope shape regardless of success or failure.

---

## 2. Technology Stack

| Layer                        | Technology                              |
|------------------------------|-----------------------------------------|
| Web Framework                | Django 4.x                              |
| API Framework                | Django REST Framework (DRF)             |
| Async Task Queue             | Celery                                  |
| Message Broker / Cache       | Redis (port 6380 — NOT default 6379)    |
| Database                     | PostgreSQL                              |
| Authentication               | SimpleJWT (JWT tokens)                  |
| API Documentation            | drf-spectacular (OpenAPI)               |
| Query Layer                  | GraphQL via graphene-django             |
| Static Files                 | WhiteNoise                              |
| Error Monitoring             | Sentry SDK                              |
| Environment Config           | django-environ                          |
| Dev Tooling                  | django-debug-toolbar, django-extensions |

---

## 3. Application Registry

### Infrastructure Apps (no domain logic)

    apps.core        — Base views, exceptions, cache, pagination, permissions,
                       middleware, error codes, logging filters
    apps.common      — Shared choices (Role, etc.), shared utilities

### Domain Apps

    apps.accounts       — Auth, JWT, profiles, addresses              (COMPLETE)
    apps.products       — Catalog, variants, attributes, bike compat  (PARTIAL)
    apps.cart           — Cart and cart items                         (PARTIAL)
    apps.coupons        — Coupon engine
    apps.orders         — Order creation, state machine, order items
    apps.payments       — Payment gateway integrations
    apps.reviews        — Verified-purchase reviews, voting, moderation
    apps.contact        — Customer support messages and replies
    apps.wishlist       — Wishlist items
    apps.tax            — Tax calculation
    apps.returns        — Return requests
    apps.recomendations — Interaction logging, personalized recommendations
    apps.notifications  — Push / email notifications
    apps.logistics      — Shipments, courier webhooks, COD settlement
    apps.analytics      — Daily snapshots, courier performance metrics

---

## 4. Six-Layer Architecture

Every domain app follows this strict layer separation.
Imports must only flow downward. Upper layers import lower layers, never reverse.

    +---------------------------------------------+
    |  Layer 6: API (urls.py, views.py)            |  <- HTTP in, HTTP out
    +---------------------------------------------+
    |  Layer 5: Serializers                        |  <- Validation, representation
    +---------------------------------------------+
    |  Layer 4: Services                           |  <- Business logic, orchestration
    +---------------------------------------------+
    |  Layer 3: Selectors / Repositories           |  <- DB queries, no business logic
    +---------------------------------------------+
    |  Layer 2: Models                             |  <- Schema, model methods
    +---------------------------------------------+
    |  Layer 1: Core / Common                      |  <- Shared infra (this document)
    +---------------------------------------------+

Rules:
    - Views call services, never query models directly
    - Services raise DomainError or InfrastructureError, never DRF exceptions
    - Serializers validate input, they do not contain business logic
    - Models contain field definitions and simple model-level methods only
    - The global exception handler converts all exceptions to HTTP responses

---

## 5. API Response Envelope — The Contract

CRITICAL: This envelope shape is returned by EVERY endpoint, success or failure,
without exception. The frontend relies on this. Never break this shape.

    {
        "success": true,
        "message": "Human readable summary",
        "data":    {},
        "errors":  null,
        "meta": {
            "request_id": "uuid-string"
        }
    }

### Field Rules

    Field     | Success (2xx)                        | Error (4xx/5xx)
    ----------|--------------------------------------|---------------------------
    success   | true                                 | false
    message   | Confirmation string                  | Safe human-readable reason
    data      | Payload object/array                 | null (always)
    errors    | null (always)                        | Error detail object
    meta      | Always present, contains request_id  | Always present, contains request_id

### Success Response — Full Example

    {
        "success": true,
        "message": "Account created successfully. Please check your email.",
        "data": {
            "email": "user@example.com"
        },
        "errors": null,
        "meta": {
            "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        }
    }

### Error Response — Full Example

    {
        "success": false,
        "message": "Registration failed.",
        "data": null,
        "errors": {
            "code": "validation_error",
            "fields": {
                "email": {
                    "message": "Enter a valid email address.",
                    "code": "invalid_email_format"
                },
                "password": {
                    "message": "Password must be at least 8 characters.",
                    "code": "min_length"
                }
            },
            "non_fields": null
        },
        "meta": {
            "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
        }
    }

### The errors Object — Complete Structure

    "errors": {
        "code": "top_level_error_code",
        "fields": {
            "<field_name>": {
                "message": "Human readable error for this field",
                "code":    "machine_readable_code"
            }
        },
        "non_fields": {
            "category": "validation | domain | system | unexpected",
            "message":  "Human readable error",
            "code":     "machine_readable_code",
            "extra":    {} | null
        }
    }

### fields — When Populated

    - Serializer field-level validation failures only
    - Each key = field name that failed
    - Only the FIRST error per field is surfaced (DRF returns lists, we take [0])
    - Multiple field errors returned simultaneously across different fields

### non_fields — Four Categories

    Category    | When Used
    ------------|-------------------------------------------------------------------
    validation  | DRF non_field_errors, auth failures, permission denied, not found
    domain      | Business rule violation (raised as DomainError)
    system      | Infrastructure failure (raised as InfrastructureError)
    unexpected  | Unhandled exception — always triggers monitor + ERROR log

### HTTP Status to errors.code Mapping

    HTTP Status | errors.code
    ------------|----------------------
    400         | validation_error
    401         | authentication_error
    403         | permission_error
    404         | not_found
    405         | method_not_allowed
    409         | conflict_error
    429         | rate_limit_exceeded
    500         | server_error
    503         | server_error

    NOTE: 409 maps to conflict_error, NOT validation_error.
    Rationale: validation_error means malformed data.
    409 means data was valid but current state refuses the operation.
    The frontend branches on the top-level code — conflating them breaks that.

### HTTP Status Default Messages (safe, shown to users)

    HTTP Status | Message
    ------------|----------------------------------------------------------------------
    400         | "Invalid request data."
    401         | "Authentication required."
    403         | "You do not have permission to perform this action."
    404         | "The requested resource was not found."
    405         | "Method not allowed."
    409         | "This action conflicts with the current state of the resource."
    429         | "Too many requests. Please slow down."
    500         | "An unexpected error occurred. Please try again later."
    503         | "The service is temporarily unavailable. Please try again shortly."

### Paginated Response — Meta Structure

When an endpoint returns a paginated list, the meta field expands:

    {
        "success": true,
        "message": "...",
        "data": [...],
        "errors": null,
        "meta": {
            "request_id":   "...",
            "page":         1,
            "page_size":    20,
            "total":        540,
            "total_pages":  27,
            "showing_from": 1,
            "showing_to":   20,
            "has_next":     true,
            "has_previous": false,
            "source":       "l2_redis",
            "sort":         "newest",
            "elapsed_ms":   12.4
        }
    }

    source, sort, and elapsed_ms are optional.
    null values are excluded from meta entirely — do not include them as null.

---

## 6. Exception Hierarchy

File: apps/core/exceptions.py

CRITICAL RULE: This file has ZERO imports from Django HTTP, DRF, or
apps.core.api. It is safe to import from any layer including Celery tasks
and management commands.

    BaseAppError(Exception)
    ├── DomainError          → Business rule violations → 400 or 409
    └── InfrastructureError  → Infrastructure failures  → 503 always

### BaseAppError

Never raise directly. Exists for catch-all handlers.

    BaseAppError(
        message: str,                         # human-readable, safe to show users
        *,
        code: str,                            # machine-readable slug
        client_extra: dict | None = None,     # forwarded to client response
        internal:     dict | None = None,     # NEVER forwarded to client, logs only
    )
    .status_code = 0  (sentinel, overridden by subclasses)

### DomainError

Use when the domain says NO to a valid request.
Not a malformed request — the data was fine but business rules refuse the operation.

    DomainError(
        message: str,
        *,
        code: str = "domain_error",
        status_code: int = 400,     # MUST be 400 or 409 ONLY — raises ValueError otherwise
        client_extra: dict | None = None,
        internal:     dict | None = None,
    )
    ALLOWED_STATUS_CODES = frozenset({400, 409})

When to use 400 vs 409:
    400 — Generic domain rejection: "Cart is empty", "Coupon expired"
    409 — State conflict: "Order already cancelled", "Email already exists"

Examples:

    # 400 — generic rejection
    raise DomainError(
        "Your cart is empty. Add items before checking out.",
        code="cart_empty",
    )

    # 409 — state conflict
    raise DomainError(
        "This order has already been cancelled.",
        code="order_already_cancelled",
        status_code=409,
    )

    # 409 with client_extra (forwarded to response) and internal (logs only)
    raise DomainError(
        "Coupon has already been used.",
        code="coupon_already_used",
        status_code=409,
        client_extra={"applied_on": "2024-01-15"},
        internal={"coupon_id": 99, "used_by_user_id": 12},
    )

### InfrastructureError

Use when an external system or internal subsystem is temporarily unavailable.
Always returns 503. Not configurable.

IMPORTANT: Named InfrastructureError NOT SystemError to avoid shadowing
Python's built-in SystemError, which the interpreter and C extensions raise
for internal VM-level failures. Shadowing it causes silent, impossible-to-debug
failures in third-party libraries that catch SystemError internally.

    InfrastructureError(
        message: str,
        *,
        code: str = "infrastructure_error",
        notify: bool = True,    # True  = alert Sentry/PagerDuty + ERROR log
                                # False = WARNING log only, no monitor alert
        client_extra: dict | None = None,
        internal:     dict | None = None,
    )
    .status_code = 503  (class attribute, not overridable per instance)

Examples:

    # Unexpected failure — alert on-call
    raise InfrastructureError(
        "Payment gateway is temporarily unavailable. Please retry.",
        code="payment_gateway_timeout",
        client_extra={"retry_after": 30},
        internal={"gateway": "stripe", "http_status": 504},
    )

    # Expected, handled outage — fallback in place, no paging on-call
    raise InfrastructureError(
        "Recommendations unavailable. Showing defaults.",
        code="recommendation_service_down",
        notify=False,
        internal={"service": "rec-engine", "reason": "circuit_open"},
    )

---

## 7. Global Exception Handler

File: apps/core/api/exceptions.py
Registered in settings: "EXCEPTION_HANDLER": "apps.core.api.exceptions.custom_exception_handler"

THE SINGLE MOST IMPORTANT ARCHITECTURAL INVARIANT:
All logging lives in custom_exception_handler and ONLY there.
Builder functions are pure — input in, dict out, zero side effects, zero logging.
This guarantees exactly ONE log entry and ONE Sentry event per exception.

SECURITY INVARIANT:
exc.internal is NEVER passed to any builder function and NEVER appears in
any response. It is only written to the logger inside custom_exception_handler.

### Decision Tree (evaluated in order)

    Exception raised
    │
    ├── isinstance(exc, DomainError)?
    │       status          = exc.status_code (400 or 409)
    │       non_fields.category = "domain"
    │       monitor alert   = NO
    │       log             = WARNING, no traceback
    │       exc.internal    = logged at DEBUG before builder called
    │       response body   = _non_fields_domain(exc)
    │
    ├── isinstance(exc, InfrastructureError)?
    │       status          = 503
    │       non_fields.category = "system"
    │       if notify=True  → _notify_monitors(exc) + ERROR log + exc_info=True
    │       if notify=False → WARNING log, no traceback, no monitor
    │       response body   = _non_fields_infrastructure(exc)
    │
    ├── DRF-recognised exception? (exception_handler returns non-None)
    │       status          = original DRF status code preserved
    │       non_fields.category = "validation"
    │       if status >= 500 → _notify_monitors + ERROR log + exc_info=True
    │       if status <  500 → WARNING log, no traceback
    │       response body   = _format_drf_errors(response.data, status_code)
    │
    └── Unhandled exception (exception_handler returns None)
            status          = 500
            non_fields.category = "unexpected"
            always          → _notify_monitors + ERROR log + exc_info=True
            DEBUG=True      → raw exc message in response
            DEBUG=False     → safe generic message only (never leak internals)

### Monitor Registry

    from apps.core.api.exceptions import register_monitor

    # Register Sentry or any monitor — called once at startup
    register_monitor(lambda exc: capture_exception(exc))

    Monitors ARE called for:
        - InfrastructureError where notify=True
        - DRF 5xx responses
        - Unhandled exceptions

    Monitors are NOT called for:
        - DomainError (expected business logic)
        - DRF 4xx (client errors, not our defects)
        - InfrastructureError where notify=False

### Key Helper Functions (all pure — zero side effects, zero logging)

    _format_drf_errors(data, status_code) -> dict
        Normalizes DRF error data into the standard errors envelope.
        Called by:
            - custom_exception_handler for DRF exceptions
            - BaseAPIView.error_response() for manual responses
            - BaseAPIView.not_found_response(), unauthorized_response(), forbidden_response()
        Handles three DRF shapes:
            dict  → {"email": [ErrorDetail], "non_field_errors": [...]}
            list  → [ErrorDetail("Authentication credentials not provided.")]
            str   → "Not found."

    _status_to_error_code(status_code) -> str
        Maps HTTP status to top-level errors.code string.
        409 maps to conflict_error, not validation_error.

    _status_to_message(status_code) -> str
        Maps HTTP status to safe default human message.

    _non_fields_domain(exc: DomainError) -> dict
        Builds domain non_fields block. Pure. No logging.

    _non_fields_infrastructure(exc: InfrastructureError) -> dict
        Builds system non_fields block. Pure. No logging.

    _non_fields_unexpected(exc, *, status_code) -> dict
        Builds unexpected non_fields block. DEBUG shows raw message.
        Production always shows safe generic message.

---

## 8. BaseAPIView — All Views Inherit This

File: apps/core/api/views.py

    from apps.core.api.views import BaseAPIView

    class MyView(BaseAPIView):
        ...

RULE: Every view in the project inherits from BaseAPIView.
      Never use APIView or GenericAPIView directly.

BaseAPIView inherits from: APIResponseMixin, GenericAPIView
Default: permission_classes = [AllowAny]  — override per view for protected routes.

### Response Helper Decision Guide

    Situation                              | Helper to Use
    ---------------------------------------|----------------------------------------
    Successful GET, list, or action        | self.success_response(...)
    Resource just created (POST)           | self.created_response(...)
    Serializer field errors                | self.error_response(errors=serializer.errors)
    DomainError caught directly in view    | self.domain_error_response(exc=exc)
    Resource does not exist                | self.not_found_response(...)
    No auth credentials                    | self.unauthorized_response(...)
    Auth present but access denied         | self.forbidden_response(...)

    PREFERRED PATTERN: Raise DomainError / InfrastructureError in the service
    layer and let custom_exception_handler handle automatically.
    Only use domain_error_response() when a view constructs a domain error
    directly without a service layer in between (rare).

### Full Method Signatures

    # ── Success ──────────────────────────────────────────────────────────────

    def success_response(
        self,
        *,
        data:        Any = None,
        message:     str = "Request successful",
        status_code: int = 200,
        meta:        dict | None = None,
    ) -> Response

    def created_response(
        self,
        *,
        data:    Any = None,
        message: str = "Resource created successfully",
        meta:    dict | None = None,
    ) -> Response

    # ── Error ─────────────────────────────────────────────────────────────────

    def error_response(
        self,
        *,
        message:     str = "Request failed",
        errors:      Any = None,    # serializer.errors, str, or dict
        status_code: int = 400,
    ) -> Response
    # Internally calls _format_drf_errors(errors, status_code)
    # Do NOT use for domain errors — use domain_error_response() instead
    # so frontend receives category="domain" not category="validation"

    def domain_error_response(
        self,
        *,
        exc: DomainError,
    ) -> Response
    # Produces category="domain", correct status, client_extra forwarded

    def not_found_response(
        self,
        *,
        message: str = "Resource not found",
    ) -> Response
    # Returns 404, errors.code="not_found", category="validation"

    def unauthorized_response(
        self,
        *,
        message: str = "Authentication required",
    ) -> Response
    # Returns 401, errors.code="authentication_error", category="validation"

    def forbidden_response(
        self,
        *,
        message: str = "You do not have permission to perform this action",
    ) -> Response
    # Returns 403, errors.code="permission_error", category="validation"

### transform_payload() — Request ID Injection

    BaseAPIView overrides APIResponseMixin.transform_payload() to inject
    request_id into every response meta automatically.

    def transform_payload(self, payload: dict) -> dict:
        request_id = getattr(self.request, "id", None)
        if request_id:
            if payload.get("meta") is None:
                payload["meta"] = {}
            payload["meta"]["request_id"] = request_id
        return payload

    request.id is set by RequestIDMiddleware.
    If middleware is absent (e.g. unit tests), this is a silent no-op.

---

## 9. APIResponseMixin

File: apps/core/api/mixins.py

BaseAPIView inherits from this. You do not use this directly.

    class APIResponseMixin:
        MESSAGE_KEY: str = "message"
        ERRORS_KEY:  str = "errors"
        DATA_KEY:    str = "data"
        SUCCESS_KEY: str = "success"
        META_KEY:    str = "meta"

    def build_response(
        self,
        *,
        data:        Any = None,
        message:     str | None = None,
        errors:      Any = None,
        status_code: int = 200,
        meta:        dict | None = None,
        headers:     dict | None = None,
    ) -> Response

    def transform_payload(self, payload: dict) -> dict:
        return payload   # no-op in mixin, overridden in BaseAPIView

The build_response() method:
    1. Assembles the 5-key envelope (success, message, data, errors, meta)
    2. Calls self.transform_payload(payload) — injects request_id in BaseAPIView
    3. Creates Response(payload, status=status_code)
    4. Applies any headers dict to the response object

---

## 10. Error Codes Registry

File: apps/core/error_codes.py

    from apps.core.error_codes import ErrorCode

All machine-readable error codes live here.
No string literals at raise sites — always use ErrorCode constants.
These are a PUBLIC API. The React frontend switches on these values.
Changing a value string is a BREAKING CHANGE.

    # ── Authentication ────────────────────────────────────────────────────────
    ErrorCode.INVALID_CREDENTIALS          = "invalid_credentials"
    ErrorCode.EMAIL_NOT_VERIFIED           = "email_not_verified"
    ErrorCode.ACCOUNT_DISABLED             = "account_disabled"
    ErrorCode.ACCOUNT_INACTIVE             = "account_inactive"
    ErrorCode.SESSION_EXPIRED              = "session_expired"
    ErrorCode.TOKEN_INVALID                = "token_invalid"
    ErrorCode.TOKEN_EXPIRED                = "token_expired"

    # ── OTP ───────────────────────────────────────────────────────────────────
    ErrorCode.OTP_RESEND_COOLDOWN          = "otp_resend_cooldown"
    ErrorCode.OTP_NOT_FOUND                = "otp_not_found"
    ErrorCode.OTP_EXPIRED                  = "otp_expired"
    ErrorCode.OTP_INVALID                  = "otp_invalid"
    ErrorCode.OTP_ATTEMPTS_EXCEEDED        = "otp_attempts_exceeded"

    # ── Verified Session ──────────────────────────────────────────────────────
    ErrorCode.VERIFICATION_SESSION_INVALID = "verification_session_invalid"
    ErrorCode.VERIFICATION_SESSION_EXPIRED = "verification_session_expired"

    # ── Social Auth ───────────────────────────────────────────────────────────
    ErrorCode.UNSUPPORTED_AUTH_PROVIDER    = "unsupported_auth_provider"
    ErrorCode.INVALID_SOCIAL_TOKEN         = "invalid_social_token"
    ErrorCode.AUTH_PROVIDER_UNREACHABLE    = "auth_provider_unreachable"
    ErrorCode.SOCIAL_EMAIL_NOT_VERIFIED    = "social_email_not_verified"
    ErrorCode.SOCIAL_EMAIL_MISSING         = "social_email_missing"
    # NOTE: ACCOUNT_INACTIVE appears in both Auth and Social Auth in source file

    # ── Registration / Email ──────────────────────────────────────────────────
    ErrorCode.EMAIL_ALREADY_EXISTS         = "email_already_exists"
    ErrorCode.EMAIL_INVALID_FORMAT         = "email_invalid_format"

    # ── User / Profile ────────────────────────────────────────────────────────
    ErrorCode.INVALID_FULL_NAME            = "invalid_full_name"
    ErrorCode.INVALID_PHONE                = "invalid_phone"
    ErrorCode.INVALID_DATE_OF_BIRTH        = "invalid_date_of_birth"
    ErrorCode.INVALID_ADDRESS              = "invalid_address"

    # ── Password ──────────────────────────────────────────────────────────────
    ErrorCode.PASSWORD_TOO_WEAK            = "password_too_weak"
    ErrorCode.PASSWORD_MISMATCH            = "password_mismatch"
    ErrorCode.PASSWORD_SAME_AS_OLD         = "password_same_as_old"

    # ── File Upload ───────────────────────────────────────────────────────────
    ErrorCode.INVALID_IMAGE_SIZE           = "invalid_image_size"
    ErrorCode.INVALID_IMAGE_TYPE           = "invalid_image_type"

    # ── Top-level Category Codes (go into errors.code not non_fields.code) ───
    # These describe WHAT KIND of error occurred, not the specific cause.
    ErrorCode.VALIDATION_ERROR             = "validation_error"
    ErrorCode.AUTHENTICATION_ERROR         = "authentication_error"
    ErrorCode.PERMISSION_ERROR             = "permission_error"
    ErrorCode.NOT_FOUND                    = "not_found"
    ErrorCode.RATE_LIMIT_EXCEEDED          = "rate_limit_exceeded"
    ErrorCode.SERVER_ERROR                 = "server_error"
    ErrorCode.METHOD_NOT_ALLOWED           = "method_not_allowed"
    ErrorCode.CONFLICT_ERROR               = "conflict_error"    # 409

When adding a new code:
    1. Add constant to ErrorCode in apps/core/error_codes.py
    2. Add a comment indicating which app/domain owns it
    3. Never delete — deprecate with a comment instead
    4. Inform the frontend team — these are a public contract

---

## 11. Two-Level Cache System

File: apps/core/cache.py
Singleton: from apps.core.cache import two_level_cache

### Architecture

    Request
      |
      v
    L1: LocMemCache  (caches["local"])
        per-process, ultra-fast, 60s TTL, max 500 entries
        miss?
      |
      v
    L2: Redis  (caches["default"])
        shared across all workers, 300s TTL
        miss?
      |
      v
    Database (via builder_fn passed to get_or_set)

### Key Concepts

    Cache Versioning:
        All keys prefixed with v{CACHE_VERSION}:
        Currently CACHE_VERSION = 1
        To bust entire cache on deploy: increment CACHE_VERSION in cache.py

    Sentinel Encoding:
        All values stored as {"__v": value}
        Distinguishes genuine cache miss (backend returns None) from
        a cached falsy value (None, False, [], 0).
        Without this, cached None looks like a miss → unnecessary DB hits.

    Stampede Protection:
        get_or_set() uses cache.add() (atomic SET NX) as a Redis lock.
        Only ONE worker rebuilds cache on cold miss.
        All other concurrent workers wait up to _lock_max_wait=5s then retry.
        If Redis unavailable: _acquire_lock fails open — request proceeds
        without stampede protection rather than crashing.

    L1 Deep Copy:
        L1 get() returns copy.deepcopy(value).
        Without this, callers mutating returned object would poison the
        shared in-process cache for all subsequent requests in same process.

    Fault Tolerance:
        L1 and L2 failures are caught, logged as WARNING, execution continues.
        Cache failures degrade gracefully — they never crash a request.

### Public API

    from apps.core.cache import two_level_cache

    # ── Cache-aside (recommended pattern) ─────────────────────────────────────
    data, source = two_level_cache.get_or_set(
        "products:list:page1",
        lambda: MySerializer(MyModel.objects.all(), many=True).data,
        lock=True,          # default True — set False in unit tests only
        l1_timeout=60,      # optional override of instance default
        l2_timeout=300,     # optional override of instance default
    )
    # source: "l1_memory" | "l2_redis" | "database"

    # ── Manual get ────────────────────────────────────────────────────────────
    data, source = two_level_cache.get("products:list:page1")
    if source == "miss":
        data = build_data()
        two_level_cache.set("products:list:page1", data)

    # ── Set ───────────────────────────────────────────────────────────────────
    two_level_cache.set(
        "my_key",
        value,
        l1_timeout=30,      # optional
        l2_timeout=120,     # optional
    )

    # ── Delete (prefix-based, SCAN safe — never KEYS *) ───────────────────────
    two_level_cache.delete("products:")
    # L2: SCAN for *v1:products:* pattern
    # L1: full clear (cheap — rebuilds on next request)

### Return Values

    get() and get_or_set() both return (value, source):

    source          | Meaning
    ----------------|-----------------------------------------------------------
    "l1_memory"     | Served from in-process LocMemCache
    "l2_redis"      | Served from Redis; L1 backfilled automatically
    "miss"          | Not in either level — caller must rebuild
    "database"      | Cache was cold, builder_fn() called, cache now populated

    Pass source to build_pagination_meta() to expose cache hit info in
    response meta.source field.

### Instance Defaults

    two_level_cache = TwoLevelCache(l1_timeout=60, l2_timeout=300)

    Override per-call using l1_timeout / l2_timeout keyword args.
    Different timeouts for different data profiles:
        Category list (rarely changes):  l2_timeout=3600
        Search results (change often):   l2_timeout=60
        User-specific data:              scope key to user ID

### Cache Key Conventions

    products:list:{filter_hash}
    products:detail:{slug}
    categories:tree
    brands:list
    cart:{user_id}
    orders:list:{user_id}:page:{page}

---

## 12. Pagination System

File: apps/core/paginations.py

Two functions used together in every paginated view.

### get_pagination_params(request, default_page_size=20, max_page_size=48)

    from apps.core.paginations import get_pagination_params, build_pagination_meta

    params = get_pagination_params(request)
    # Returns PaginationParams(page, page_size, is_valid)
    # PaginationParams is a NamedTuple — access as params.page, params.page_size

    if not params.is_valid:
        return self.error_response(message="Invalid pagination parameters.")

Behavior:
    - Never raises exceptions — returns is_valid=False on bad input
    - Logs WARNING on invalid params (visible in apps.core logger)
    - page is always >= 1
    - page_size is always between 1 and max_page_size
    - If page is valid but page_size is not: keeps valid page, falls back page_size to default
    - Query params: ?page=2&page_size=12

Default limits:
    default_page_size=20  — returned when page_size not in query params
    max_page_size=48      — hard ceiling regardless of what client sends (48 = 4 grid pages)

Override per endpoint:
    params = get_pagination_params(request, default_page_size=12, max_page_size=100)

### build_pagination_meta(page, page_size, total, *, source, sort, elapsed_ms, clamp_page=True)

    meta = build_pagination_meta(
        params.page,
        params.page_size,
        total_count,
        source=cache_source,    # "l1_memory" | "l2_redis" | "database"
        sort=sort_param,        # "newest" | "price_asc" | etc.
        elapsed_ms=12.4,        # optional timing
    )

Returns:
    {
        "page":         1,
        "page_size":    20,
        "total":        540,
        "total_pages":  27,
        "showing_from": 1,
        "showing_to":   20,
        "has_next":     True,
        "has_previous": False,
        # Optional — only included if passed as non-None:
        "source":       "l2_redis",
        "sort":         "newest",
        "elapsed_ms":   12.4,
    }

clamp_page=True (default):
    If page overshoots total_pages, it is clamped down to total_pages.
    Prevents showing_from/showing_to from producing garbage values.

### Complete Paginated View Pattern

    import time
    from apps.core.paginations import get_pagination_params, build_pagination_meta
    from apps.core.cache import two_level_cache

    class ProductListAPIView(BaseAPIView):
        def get(self, request):
            params = get_pagination_params(request, default_page_size=12, max_page_size=48)
            if not params.is_valid:
                return self.error_response(message="Invalid pagination parameters.")

            sort = request.query_params.get("sort", "newest")
            cache_key = f"products:list:{sort}:page:{params.page}:size:{params.page_size}"

            t0 = time.monotonic()

            data, source = two_level_cache.get_or_set(
                cache_key,
                lambda: self._build_product_data(params, sort),
            )

            elapsed_ms = (time.monotonic() - t0) * 1000

            meta = build_pagination_meta(
                params.page,
                params.page_size,
                data["total"],
                source=source,
                sort=sort,
                elapsed_ms=round(elapsed_ms, 2),
            )

            return self.success_response(
                data=data["results"],
                message="Products retrieved successfully.",
                meta=meta,
            )

---

## 13. Serializer Fields and Mixins

Files: apps/core/fields.py, apps/core/mixins.py

### CustomDateTimeField

    from apps.core.fields import CustomDateTimeField

    class MySerializer(serializers.ModelSerializer):
        some_date = CustomDateTimeField()

Defaults:
    format=None                                         ISO-8601 output
    input_formats=['iso-8601']
    default_timezone=timezone.get_current_timezone()
    read_only=True

### TimestampFieldsMixin

    from apps.core.mixins import TimestampFieldsMixin

    class MySerializer(TimestampFieldsMixin, serializers.ModelSerializer):
        class Meta:
            model = MyModel
            fields = [..., "created_at", "updated_at"]

Automatically adds created_at and updated_at as CustomDateTimeField instances.
ISO-8601, read-only, timezone-aware.
Use this mixin on EVERY serializer that exposes timestamp fields.
Do NOT redefine these fields manually.

---

## 14. Permission Classes

File: apps/core/permissions.py
Role source: apps.common.choices.role.Role
All classes inherit from rest_framework.permissions.BasePermission.
All denials are logged at WARNING level.

    from apps.core.permissions import (
        IsAdmin,
        IsAdminOrReadOnly,
        IsCustomer,
        IsVerified,
        IsNotAuthenticated,
        RoleBasedProfilePermission,
    )

    Permission Class           | Rule
    ---------------------------|------------------------------------------------------
    IsAdmin                    | user.role == Role.ADMIN
    IsAdminOrReadOnly          | GET/HEAD/OPTIONS: anyone
                               | POST/PUT/PATCH/DELETE: ADMIN only
    IsCustomer                 | user.role == Role.CUSTOMER AND user.is_verified == True
    IsVerified                 | user.is_verified == True (any role)
    IsNotAuthenticated         | not user.is_authenticated (for login/register endpoints)
    RoleBasedProfilePermission | Verified CUSTOMER or ADMIN

Usage in Views:

    class ProductListAPIView(BaseAPIView):
        permission_classes = [IsAdminOrReadOnly]

    class CartDetailAPIView(BaseAPIView):
        permission_classes = [IsAuthenticated, IsVerified]

    NOTE: BaseAPIView defaults to permission_classes = [AllowAny]
    Always override explicitly for protected endpoints.

---

## 15. Middleware

File: apps/core/middleware.py
Position in MIDDLEWARE list: 2nd (after CorsMiddleware)

### RequestIDMiddleware

    class RequestIDMiddleware:
        def __call__(self, request):
            request.id = str(uuid.uuid4())         # unique per request
            response = self.get_response(request)
            response["X-Request-ID"] = request.id  # also set in response header
            return response

Every request has request.id.
BaseAPIView.transform_payload() reads this and injects into every response meta.request_id.
Exception handler reads getattr(request, "id", None) — safely handles missing middleware.

---

## 16. Authentication and Token Strategy

### JWT Configuration (SimpleJWT)

    SIMPLE_JWT = {
        'ACCESS_TOKEN_LIFETIME':    timedelta(minutes=1),  # very short — refresh often
        'REFRESH_TOKEN_LIFETIME':   timedelta(days=1),
        'ROTATE_REFRESH_TOKENS':    True,     # new refresh token on every refresh call
        'BLACKLIST_AFTER_ROTATION': True,     # old refresh tokens blacklisted immediately
        'AUTH_HEADER_TYPES':        ('Bearer',),
    }

### Token Storage Strategy

    Token         | Location             | Rationale
    --------------|----------------------|------------------------------------------
    Access Token  | Response body data   | Frontend stores in memory only.
                  |                      | NEVER localStorage — XSS risk.
    Refresh Token | HttpOnly cookie      | JavaScript cannot read it — XSS safe.
                  |                      | Browser sends automatically.

### Cookie Settings for Refresh Token

    Name:     refresh_token
    HttpOnly: true
    Secure:   true (production) / false (local dev)
    SameSite: Lax
    MaxAge:   7 days
    Path:     /api/accounts/

    Cookie scoped to /api/accounts/ — NOT sent on product/cart requests.

### CSRF Strategy

    CSRF Token: Set as readable cookie
    Frontend:   Reads cookie, sends in X-CSRFToken header on state-changing requests
    Pattern:    Double-submit CSRF protection

### Auth Flow for Protected Endpoints

    1. Frontend sends Authorization: Bearer <access_token> header
    2. DRF JWTAuthentication validates the token
    3. If expired → frontend uses refresh token (auto-sent via cookie) to call
       POST /api/accounts/token/refresh/ for a new access token
    4. Frontend retries original request with new access token

---

## 17. Logging System

### Logger Names — One Per App

    import logging
    logger = logging.getLogger("apps.accounts")   # in accounts views/services
    logger = logging.getLogger("apps.products")   # in products views/services
    logger = logging.getLogger("apps.orders")     # in orders views/services
    logger = logging.getLogger("apps.cart")       # in cart views/services
    logger = logging.getLogger("apps.core")       # in core infrastructure

    Use the correct logger for the correct app.
    Do NOT use the root logger — it has level WARNING, DEBUG/INFO silently dropped.

### Log Files

    Logger          | File
    ----------------|------------------------
    apps.accounts   | logs/accounts.log
    apps.products   | logs/products.log
    apps.orders     | logs/orders.log
    apps.cart       | logs/cart.log
    apps.core       | logs/core.log
    django, celery  | logs/django.log

    All loggers also write to console. Level is DEBUG for all app loggers.

### Log Format

    [2024-01-15 14:30:22] INFO apps.products ProductListAPIView Products retrieved
    [YYYY-MM-DD HH:MM:SS] LEVEL name message

### Logging Policy

    In services (raise exceptions, add context):
        logger.info("Order created: order_id=%s user_id=%s", order.id, user.id)
        logger.warning("Inventory low: variant_id=%s stock=%s", variant.id, stock)

    In exception handler (automatic — do not duplicate):
        DomainError                        → WARNING, no traceback
        InfrastructureError notify=True    → ERROR, exc_info=True
        InfrastructureError notify=False   → WARNING, no traceback
        DRF 4xx                            → WARNING, no traceback
        DRF 5xx                            → ERROR, exc_info=True
        Unhandled                          → ERROR, exc_info=True

    NEVER do this — logging in builder functions or serializers:
        logger.error("...", exc_info=True)  # in _non_fields_domain() or any builder
        # Logging belongs in the handler and service layer ONLY.

### SensitiveDataFilter

    Applied to the file handler for django.log.
    Masks sensitive fields before writing to disk.
    File: apps/core/logging.py
    Do not log passwords, tokens, or PII in any log call.

---

## 18. Settings Reference

File: config/settings/base.py (single settings file — no dev/prod split shown)

### Key Settings

    Setting                  | Value
    -------------------------|---------------------------------------------------
    AUTH_USER_MODEL          | "accounts.User"
    TIME_ZONE                | "UTC"  (database timezone)
    CELERY_TIMEZONE          | "Asia/Karachi"  (PKT for scheduled tasks)
    DEFAULT_AUTO_FIELD       | "django.db.models.BigAutoField"
    EXCEPTION_HANDLER        | "apps.core.api.exceptions.custom_exception_handler"
    DEFAULT_SCHEMA_CLASS     | "drf_spectacular.openapi.AutoSchema"
    Redis port               | 6380 (NOT default 6379 — important for config)
    Access token lifetime    | 1 minute
    Refresh token lifetime   | 1 day

### Cache Backend Names (exact strings used in TwoLevelCache)

    caches["default"]  →  Redis (L2, shared across workers)
    caches["local"]    →  LocMemCache (L1, per-process)

    Do not change these names without updating apps/core/cache.py properties.

### Installed Apps Load Order

    1. DJANGO_APPS        (django.contrib.*)
    2. THIRD_PARTY_APPS   (rest_framework, simplejwt, corsheaders, etc.)
    3. PROJECT_APPS       (apps.core, apps.common, apps.accounts, ...)

### Default Throttle Rates

    CustomAnonRateThrottle  →  10000/hour
    CustomUserRateThrottle  →  1000/hour
    Custom throttle classes in apps/core/throttles.py

### Debug Toolbar

    Enabled ONLY when DEBUG=True — middleware appended conditionally.
    INTERNAL_IPS includes Docker internal IP detection logic.

### Timezone Critical Note

    TIME_ZONE = "UTC" for the database.
    CELERY_TIMEZONE = "Asia/Karachi" for scheduled tasks.
    When bounding date ranges in nightly analytics aggregations,
    use timezone.localtime() to avoid midnight bleeding across days in PKT.
    Failure to do this produces daily snapshots that span wrong time ranges.

---

## 19. Critical Rules — Never Violate

These are enforced by architecture. Violating them causes bugs that are
hard to trace and inconsistencies that break the frontend contract.

### Response Shape Rules

    1. Every view MUST inherit from BaseAPIView — never APIView or GenericAPIView.

    2. Never construct a raw Response() in a view.
       Always use the helper methods: success_response(), created_response(), etc.

    3. Never put data in the errors field or errors in the data field.

    4. meta must always contain request_id.
       This is automatic via transform_payload(). Do not manually override it.

### Exception Rules

    5. Raise DomainError and InfrastructureError in the service/domain layer.
       Let custom_exception_handler convert them to responses automatically.
       Do NOT catch and re-raise as DRF APIException — you lose domain/system category.

    6. Never pass exc.internal to any builder function.
       It must only appear in log calls inside custom_exception_handler.

    7. Never log inside builder functions (_non_fields_domain, etc.).
       ONE log entry per exception. Logging belongs in custom_exception_handler only.

    8. DomainError status_code MUST be 400 or 409 only.
       The constructor raises ValueError if you pass anything else.

    9. InfrastructureError is always 503. You cannot change this per instance.
       If you need a different 5xx, use DRF APIException directly.

### Error Code Rules

    10. Never use string literals at raise sites.
        Always import and use ErrorCode constants from apps/core/error_codes.py.

    11. Never DELETE an ErrorCode — deprecate with a comment.
        The frontend switches on these values. Deleting breaks the frontend.

### Cache Rules

    12. Never call KEYS * on Redis in any context.
        Always use delete_pattern() which uses SCAN internally.

    13. Never cache user-specific sensitive data in shared two_level_cache
        without scoping the cache key to the user ID.

    14. Never convert Decimal monetary values to float during aggregation.
        Use decimal.Decimal and Django Sum() with DecimalField throughout.

### Inventory and Transaction Rules

    15. Wrap checkout logic in transaction.atomic().
        Use ProductVariant.objects.select_for_update() when deducting inventory.
        Without this, concurrent checkouts WILL oversell.

    16. Never mutate order status without writing an OrderStatusLog entry.
        Use a service method that atomically updates both in one transaction.

### Logging Rules

    17. Use the correct logger for the correct app.
        logger = logging.getLogger("apps.products") in products code.
        logger = logging.getLogger("apps.orders") in orders code.

    18. Never use the root logger — logging.getLogger() with no name.
        Root logger level is WARNING. DEBUG/INFO messages are silently dropped.

    19. Celery tasks that call external APIs MUST use exponential backoff retry.
        Never run synchronous external HTTP calls in the request/response cycle.

### Timezone Rules

    20. TIME_ZONE = "UTC" for the database.
        CELERY_TIMEZONE = "Asia/Karachi" for scheduled tasks.
        Always use timezone.localtime() when bounding date ranges for
        nightly analytics — never assume UTC midnight = PKT midnight.

---

## 20. How to Add a New Endpoint — Checklist

Follow this every time. Skip no step.

### Step 1 — Models

    [ ] Model defined in apps/{app}/models.py
    [ ] Migration created and applied
    [ ] __str__ defined on every model
    [ ] Correct on_delete: PROTECT for financial records, CASCADE for owned items
    [ ] BigAutoField as default (set globally — no action needed per model)

### Step 2 — Error Codes

    [ ] Any new error codes added to apps/core/error_codes.py
    [ ] Grouped with a comment indicating which app they belong to
    [ ] Frontend team notified of new codes

### Step 3 — Exceptions (if needed)

    [ ] Service raises DomainError for business rule violations
    [ ] Service raises InfrastructureError for external service failures
    [ ] exc.internal contains ONLY diagnostic data (never client-facing data)
    [ ] exc.client_extra contains ONLY data safe to expose to client

### Step 4 — Service Layer

    [ ] Business logic in apps/{app}/services.py — never in views
    [ ] DB queries via selector/repository functions — never raw ORM in views
    [ ] transaction.atomic() wrapping any multi-step write operations
    [ ] select_for_update() on any inventory/stock rows being modified

### Step 5 — Serializer

    [ ] Serializer in apps/{app}/serializers.py
    [ ] Timestamp fields use TimestampFieldsMixin or CustomDateTimeField
    [ ] No business logic in serializers — validation only
    [ ] error_response(errors=serializer.errors) for validation failures

### Step 6 — View

    [ ] View inherits from BaseAPIView — never APIView or GenericAPIView
    [ ] permission_classes set explicitly (do NOT rely on AllowAny default for protected routes)
    [ ] Paginated lists use get_pagination_params() + build_pagination_meta()
    [ ] Cache via two_level_cache.get_or_set() for read-heavy endpoints
    [ ] Correct response helper used: success_response / created_response / error_response
    [ ] Logger declared: logger = logging.getLogger("apps.{app_name}")
    [ ] Logger calls present for key actions: create, update, delete, error paths

### Step 7 — URLs

    [ ] URL added to apps/{app}/urls.py with app_name set
    [ ] Named with descriptive name: name="order-detail"
    [ ] Registered in config/urls.py under correct API prefix

### Step 8 — Testing (Postman)

    [ ] Full envelope shape verified: success, message, data, errors, meta
    [ ] request_id appears in meta
    [ ] errors.code matches expected value for error scenarios
    [ ] errors.non_fields.category is correct: domain / system / validation
    [ ] exc.internal does NOT appear in response body
    [ ] Pagination: page, page_size, showing_from, showing_to, has_next verified
    [ ] Cache: second request shows source="l2_redis" or "l1_memory" in meta

---

## 21. Appendix A — Response Examples by Scenario

### 200 — Paginated List

    {
        "success": true,
        "message": "Products retrieved successfully.",
        "data": [
            {"id": 1, "name": "Chain Sprocket", "price": "1200.00"}
        ],
        "errors": null,
        "meta": {
            "request_id":   "abc123",
            "page":         1,
            "page_size":    12,
            "total":        54,
            "total_pages":  5,
            "showing_from": 1,
            "showing_to":   12,
            "has_next":     true,
            "has_previous": false,
            "source":       "l2_redis",
            "sort":         "newest"
        }
    }

### 201 — Resource Created

    {
        "success": true,
        "message": "Order placed successfully.",
        "data": {
            "order_id": "ORD-2024-00123",
            "total": "4500.00"
        },
        "errors": null,
        "meta": {"request_id": "abc123"}
    }

### 400 — Field Validation Failure

    {
        "success": false,
        "message": "Registration failed.",
        "data": null,
        "errors": {
            "code": "validation_error",
            "fields": {
                "email": {
                    "message": "Enter a valid email address.",
                    "code":    "invalid_email_format"
                }
            },
            "non_fields": null
        },
        "meta": {"request_id": "abc123"}
    }

### 400 — Domain Rejection

    {
        "success": false,
        "message": "Your cart is empty.",
        "data": null,
        "errors": {
            "code": "validation_error",
            "fields": null,
            "non_fields": {
                "category": "domain",
                "message":  "Your cart is empty. Add items before checking out.",
                "code":     "cart_empty",
                "extra":    null
            }
        },
        "meta": {"request_id": "abc123"}
    }

### 401 — Authentication Required

    {
        "success": false,
        "message": "Authentication required.",
        "data": null,
        "errors": {
            "code": "authentication_error",
            "fields": null,
            "non_fields": {
                "category": "validation",
                "message":  "Authentication credentials were not provided.",
                "code":     "authentication_error",
                "extra":    null
            }
        },
        "meta": {"request_id": "abc123"}
    }

### 409 — State Conflict

    {
        "success": false,
        "message": "This order has already been cancelled.",
        "data": null,
        "errors": {
            "code": "conflict_error",
            "fields": null,
            "non_fields": {
                "category": "domain",
                "message":  "This order has already been cancelled.",
                "code":     "order_already_cancelled",
                "extra":    null
            }
        },
        "meta": {"request_id": "abc123"}
    }

### 503 — Infrastructure Failure

    {
        "success": false,
        "message": "The service is temporarily unavailable.",
        "data": null,
        "errors": {
            "code": "server_error",
            "fields": null,
            "non_fields": {
                "category": "system",
                "message":  "Payment gateway is temporarily unavailable. Please retry.",
                "code":     "payment_gateway_timeout",
                "extra":    {"retry_after": 30}
            }
        },
        "meta": {"request_id": "abc123"}
    }

---

## 22. Appendix B — Import Reference

    # Core infrastructure — use these, never reinvent

    from apps.core.api.views      import BaseAPIView
    from apps.core.api.exceptions import (
        _format_drf_errors,
        _non_fields_domain,
        _status_to_error_code,
        register_monitor,
    )
    from apps.core.exceptions     import DomainError, InfrastructureError
    from apps.core.error_codes    import ErrorCode
    from apps.core.cache          import two_level_cache
    from apps.core.paginations    import get_pagination_params, build_pagination_meta
    from apps.core.fields         import CustomDateTimeField
    from apps.core.mixins         import TimestampFieldsMixin
    from apps.core.permissions    import (
        IsAdmin,
        IsAdminOrReadOnly,
        IsCustomer,
        IsVerified,
        IsNotAuthenticated,
        RoleBasedProfilePermission,
    )

---

Document version: 1.0
Last updated: Based on actual source files read in full.
Do not modify this document without reading the actual source files.
Do not guess at implementation details — ask for the file.
```