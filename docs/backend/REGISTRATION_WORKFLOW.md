# Registration & Authentication Workflow

## Overview

This document covers the complete user onboarding journey.
Two registration paths exist — email/password and social OAuth.
Both paths converge at the same JWT token issuance point.

---

## Path 1 — Email & Password Registration

### Endpoint

```
POST /api/accounts/register/
Permission: AllowAny
Throttle:   AnonRateThrottle
```

### Request

```json
{
    "email":            "user@example.com",
    "full_name":        "John Doe",
    "password":         "StrongPass123!",
    "confirm_password": "StrongPass123!"
}
```

### Validation Rules

```
email
    → Stripped and lowercased
    → Regex format check
    → No DB call at serializer level

full_name
    → Minimum two words required

password
    → Minimum 8 characters
    → Passes Django AUTH_PASSWORD_VALIDATORS
    → Common passwords rejected

confirm_password
    → Must match password exactly
    → Removed from validated_data before service call
```

### What Happens Internally

```
Phase 1 — Serializer (format only, zero DB):
    validate_email_format()      → normalize + regex check
    validate_full_name()         → two word minimum
    validate_strong_password()   → strength check
    validate_passwords_match()   → cross field check
    confirm_password popped      → never reaches service

Phase 2 — Service: register_user() atomic transaction:
    Step 1: ensure_email_unique()
            → DB read: check email not taken
            → DomainError 409 if duplicate

    Step 2: User.objects.create_user()
            → Password hashed by Django
            → IntegrityError caught as race condition safety net
            → DomainError 409 if race condition hit

    Step 3: UserProfile.objects.create()

    Step 4: Cart.objects.create()

    Step 5: EmailVerificationToken.objects.create()

    If ANY step fails → entire transaction rolled back
    No partial records exist after failure

Phase 3 — After commit (side effects):
    send_verification_email_task.delay()
    → Celery async task dispatched
    → Task failure does NOT roll back registration
    → User account is valid even if email fails
    → Recovery via resend-verification endpoint
```

### Success Response — 201

```json
{
    "success": true,
    "message": "Account created successfully. Please check your email.",
    "data": {
        "email": "user@example.com"
    },
    "errors": null,
    "meta": { "request_id": "..." }
}
```

### Error Responses

```
400 — Invalid email format
400 — Single word full name
400 — Password too weak
400 — Passwords do not match
409 — Email already registered
```

---

## Email Verification Flow

### Endpoint

```
GET /api/accounts/verify-email/?token=<uuid>
Permission: AllowAny
```

### What Happens

```
1. Token looked up by UUID
2. Token validity checked:
   → is_used must be False
   → expires_at must be in future (24 hour window)
3. Inside transaction.atomic():
   → token.mark_used()
   → user.is_verified = True
   → user.save()
4. User can now log in
```

### States

```
Unverified user:
    → Can exist in system
    → Cannot log in (login rejects unverified accounts)
    → Has 24 hours to verify

Token expired:
    → User requests resend via /api/accounts/resend-verification/
    → New token issued, old token invalidated
```

---

## Path 2 — Social OAuth Registration (NEW)

### Endpoint

```
POST /api/accounts/auth/social/
Permission: AllowAny
Throttle:   AnonRateThrottle
```

### Request

```json
{
    "provider": "google" | "facebook" | "apple",
    "token":    "<provider_token_from_frontend>"
}
```

### Token Type Per Provider

```
Google   → ID Token (JWT from Google Sign-In)
Facebook → User Access Token (from Facebook Login)
Apple    → ID Token (JWT from Sign in with Apple)
```

### Architecture — Strategy + Factory + Registry Pattern

```
Why this pattern:
    Adding a new provider = one new file only
    Zero changes to existing code
    Service layer never knows which provider is used
    Each provider fully isolated

Flow:
    Request arrives with provider + token
         ↓
    AuthStrategyRegistry.get("google")
         ↓ resolves to
    GoogleAuthStrategy instance
         ↓
    strategy.authenticate(token)
         ↓ returns
    SocialUserData (normalized, provider-agnostic)
         ↓
    login_or_register_social_user(social_data)
         ↓
    User instance
         ↓
    JWT tokens issued
```

### What Happens Internally

```
Step 1 — Registry resolves strategy:
    "google"   → GoogleAuthStrategy
    "facebook" → FacebookAuthStrategy
    unknown    → DomainError 400

Step 2 — Strategy verifies token with provider:

    Google:
        GET https://oauth2.googleapis.com/tokeninfo?id_token=<token>
        → Validates token signature
        → Confirms audience matches GOOGLE_CLIENT_ID
        → Confirms email_verified = true
        → Returns user data from token claims

    Facebook:
        GET https://graph.facebook.com/debug_token
        → Validates token is_valid = true
        → Confirms app_id matches FACEBOOK_APP_ID
        GET https://graph.facebook.com/me?fields=id,name,email,picture
        → Fetches actual user profile data

Step 3 — Strategy normalizes to SocialUserData:
    provider_id               → Google: sub / Facebook: id
    provider                  → "google" | "facebook"
    email                     → lowercased, stripped
    full_name                 → constructed from parts
    avatar_url                → profile picture URL
    is_provider_email_verified → whether provider confirmed email
    extra_data                → full raw payload stored for audit

Step 4 — Service: login_or_register_social_user():

    Case 1 — Returning social user:
        SocialAccount(provider, provider_id) found
        → update last_login_at
        → return existing User
        (fastest path)

    Case 2 — Email already registered (account linking):
        provider+provider_id not found
        email matches existing User
        → create SocialAccount linked to existing User
        → User keeps password login AND social login
        (account merging)

    Case 3 — Brand new user:
        Nothing found
        → create User (password=None, is_verified=True)
        → create UserProfile
        → create Cart
        → create SocialAccount
        → all atomic

Step 5 — Token issuance:
    RefreshToken.for_user(user)
    access token  → response body data
    refresh token → HttpOnly cookie
    csrf token    → readable cookie
```

### Success Response — 200

```json
{
    "success": true,
    "message": "Authentication successful.",
    "data": {
        "access": "<jwt_access_token>"
    },
    "errors": null,
    "meta": { "request_id": "..." }
}
```

```
Cookie set:
    Name:     refresh_token
    Value:    <jwt_refresh_token>
    HttpOnly: true
    Path:     /api/accounts/
```

### Error Responses

```
400 — provider or token missing
400 — unsupported_auth_provider
400 — invalid_social_token (bad/expired token)
400 — auth_provider_unreachable (Google/Facebook down)
400 — social_email_not_verified (Google unverified email)
400 — social_email_missing (Facebook no email permission)
400 — account_inactive (deactivated account)
```

---

## Login Flow (Email & Password)

### Endpoint

```
POST /api/accounts/login/
Permission: AllowAny
Throttle:   AnonRateThrottle
```

### Request

```json
{
    "email":    "user@example.com",
    "password": "StrongPass123!"
}
```

### What Happens

```
1. Credentials validated
2. is_active checked → 400 if False
3. is_verified checked → 400 if False
4. JWT tokens issued
5. Login activity logged (UserLoginActivity)
6. access token → response body
7. refresh token → HttpOnly cookie
```

---

## SocialAccount Model

```
Stores the link between User and OAuth provider identity.

One User can have multiple SocialAccount rows:
    user@example.com → Google SocialAccount
    user@example.com → Facebook SocialAccount

Fields:
    user                      → FK to User
    provider                  → "google" | "facebook" | "apple"
    provider_id               → immutable unique ID from provider
    provider_email            → email at time of connection
    is_provider_email_verified → provider confirmed this email
    avatar_url                → profile picture URL (max 2048 chars)
    access_token              → provider token (encrypted at rest)
    refresh_token             → provider refresh token
    token_expires_at          → provider token expiry
    extra_data                → full raw OAuth payload (JSON)
    last_login_at             → last social login timestamp

Constraints:
    UNIQUE (provider, provider_id) → one identity per provider
    UNIQUE (user, provider)        → one provider link per user
```

---

## Comparison — Old vs New

```
                     Email/Password     Social OAuth
─────────────────────────────────────────────────────────
Password required    YES                NO
Email verification   Required           Skipped (provider verified)
is_verified on create  False            True
Registration speed   Multi-step         Single request
Token after register NO (verify first)  YES (immediate)
Account linking      N/A                Links to existing email account
Supports providers   1 (email only)     Unlimited via registry
Adding new provider  Code changes       One new file only
─────────────────────────────────────────────────────────
```

---

## Database Records Created Per Path

```
Email/Password Registration:
    ✅ User
    ✅ UserProfile
    ✅ Cart
    ✅ EmailVerificationToken
    ❌ SocialAccount

Social OAuth — New User:
    ✅ User  (password=None, is_verified=True)
    ✅ UserProfile
    ✅ Cart
    ✅ SocialAccount
    ❌ EmailVerificationToken

Social OAuth — Existing Email User:
    ✅ SocialAccount  (linked to existing User)
    (everything else already exists)

Social OAuth — Returning Social User:
    ✅ SocialAccount.last_login_at updated only
    (everything else already exists)
```

---

## Adding a New OAuth Provider

```
Step 1: Create strategy file
        apps/accounts/auth_strategies/apple.py
        → implement BaseAuthStrategy
        → implement authenticate() → SocialUserData
        → call auth_strategy_registry.register("apple", AppleAuthStrategy)

Step 2: Import in apps.py ready()
        import apps.accounts.auth_strategies.apple

Step 3: Add credentials to settings + .env
        APPLE_CLIENT_ID = env("APPLE_CLIENT_ID")

Step 4: Add to SocialProvider choices in models.py
        APPLE = "apple", _("Apple")

Step 5: Run migrations

Files changed: 3 (strategy file, apps.py, models.py)
Files untouched: registry, service, view, urls, serializers
```