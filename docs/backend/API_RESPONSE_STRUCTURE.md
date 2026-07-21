# API Response Structure & Error Handling

## Overview

Every endpoint in this backend returns an identical envelope shape
regardless of success or failure. The frontend never receives two
different shapes for the same semantic situation.

---

## Response Envelope

```json
{
    "success": true | false,
    "message": "Human readable summary",
    "data":    {} | null,
    "errors":  {} | null,
    "meta": {
        "request_id": "uuid-string"
    }
}
```

### Field Rules

```
success   → true  if status 2xx
            false if status 4xx or 5xx

message   → Always present
            Success: confirmation string
            Error:   safe human-readable reason

data      → Present on success responses
            null on all error responses

errors    → Present on error responses
            null on all success responses

meta      → Always present
            request_id injected automatically
            by BaseAPIView.transform_payload()
```

---

## Success Response Shape

```json
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
```

---

## Error Response Shape

```json
{
    "success": false,
    "message": "Registration failed.",
    "data": null,
    "errors": {
        "code":   "validation_error",
        "fields": {
            "email": {
                "message": "Enter a valid email address.",
                "code":    "invalid_email_format"
            },
            "password": {
                "message": "Password must be at least 8 characters.",
                "code":    "min_length"
            }
        },
        "non_fields": null
    },
    "meta": {
        "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
    }
}
```

---

## Errors Object — Full Structure

```json
"errors": {
    "code":     "top_level_error_code",
    "fields":   {
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
```

### When `fields` is populated

```
Serializer field-level validation failures.
Each key = field name that failed.
Only first error per field is returned.
Multiple field errors returned simultaneously.
```

### When `non_fields` is populated

```
Errors that are not tied to a specific field.
Four categories:

validation  → DRF non_field_errors, auth failures,
              permission denied, not found

domain      → Business rule violation
              Example: email already exists,
              cart is empty, order already cancelled

system      → Infrastructure failure
              Example: payment gateway down,
              email service unreachable

unexpected  → Unhandled exception
              Production: generic safe message
              Debug:      raw exception message
```

---

## HTTP Status Code Mapping

```
200 → Success
201 → Resource created
400 → Validation error / bad request / domain rejection
401 → Authentication required
403 → Permission denied
404 → Resource not found
405 → Method not allowed
409 → Conflict — state prevents operation
429 → Rate limit exceeded
500 → Unexpected server error
503 → Infrastructure / service unavailable
```

## Top Level Error Code Mapping

```
400 → validation_error
401 → authentication_error
403 → permission_error
404 → not_found
405 → method_not_allowed
409 → conflict_error
429 → rate_limit_exceeded
500 → server_error
503 → server_error
```

---

## Real Response Examples

### 400 — Field Validation Failure

```json
{
    "success": false,
    "message": "Registration failed.",
    "data":    null,
    "errors": {
        "code":   "validation_error",
        "fields": {
            "email": {
                "message": "Enter a valid email address.",
                "code":    "invalid_email_format"
            }
        },
        "non_fields": null
    },
    "meta": { "request_id": "..." }
}
```

### 409 — Business Rule Violation (Domain Error)

```json
{
    "success": false,
    "message": "An account with this email already exists.",
    "data":    null,
    "errors": {
        "code":   "conflict_error",
        "fields": null,
        "non_fields": {
            "category": "domain",
            "message":  "An account with this email already exists.",
            "code":     "email_already_exists",
            "extra":    null
        }
    },
    "meta": { "request_id": "..." }
}
```

### 401 — Authentication Required

```json
{
    "success": false,
    "message": "Authentication required.",
    "data":    null,
    "errors": {
        "code":   "authentication_error",
        "fields": null,
        "non_fields": {
            "category": "validation",
            "message":  "Authentication credentials were not provided.",
            "code":     "authentication_error",
            "extra":    null
        }
    },
    "meta": { "request_id": "..." }
}
```

### 429 — Rate Limited

```json
{
    "success": false,
    "message": "Too many requests. Please slow down.",
    "data":    null,
    "errors": {
        "code":   "rate_limit_exceeded",
        "fields": null,
        "non_fields": {
            "category": "validation",
            "message":  "Too many requests. Please slow down.",
            "code":     "rate_limit_exceeded",
            "extra":    null
        }
    },
    "meta": { "request_id": "..." }
}
```

### 503 — Infrastructure Failure

```json
{
    "success": false,
    "message": "The service is temporarily unavailable.",
    "data":    null,
    "errors": {
        "code":   "server_error",
        "fields": null,
        "non_fields": {
            "category": "system",
            "message":  "Payment gateway is temporarily unavailable.",
            "code":     "payment_gateway_timeout",
            "extra":    { "retry_after": 30 }
        }
    },
    "meta": { "request_id": "..." }
}
```

---

## Token Strategy

```
Access Token  → Returned in response body data
                Short lived (default 5 minutes simplejwt)
                Frontend stores in memory only
                Never in localStorage — XSS risk

Refresh Token → Returned in HttpOnly cookie
                Never in response body
                Browser sends automatically
                JavaScript cannot read it — XSS safe
                Scoped to /api/accounts/ path only

CSRF Token    → Set as readable cookie
                Frontend reads and sends in
                X-CSRFToken header on state-changing requests
                Standard double-submit CSRF pattern
```

## Cookie Settings

```
Name:     refresh_token
HttpOnly: true
Secure:   true  (production) / false (local dev)
SameSite: Lax
MaxAge:   7 days
Path:     /api/accounts/
```

---

