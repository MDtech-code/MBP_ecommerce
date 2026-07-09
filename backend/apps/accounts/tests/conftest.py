# backend/apps/accounts/tests/conftest.py
"""
Accounts app test configuration — fixtures and constants.

Scope:
    Available to ALL test files inside apps/accounts/tests/
    and its subdirectories automatically.

What belongs here:
    ✓ URL constants — single source of truth for all endpoint paths
    ✓ Password constants — shared across unit and API tests
    ✓ User fixtures — verified, unverified, inactive, admin
    ✓ Address fixtures — valid payload, created address instance
    ✓ Auth client fixtures — pre-authenticated APIClient instances
    ✓ Task mocks — prevent Celery from hitting broker in any test

What does NOT belong here:
    ✗ Test logic — that goes in individual test files
    ✗ Core infrastructure fixtures — those are in global conftest.py
    ✗ Test views — those are in core/tests/conftest.py
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import (
    EmailVerificationToken,
    PasswordResetToken,
    User,
    UserAddress,
    UserProfile,
)


# ─── Password Constants ───────────────────────────────────────────────────────
# Defined once here — imported by all test files that need them.
# Passes ALL Django default password validators:
#   ✓ MinimumLengthValidator       (8+ chars)
#   ✓ CommonPasswordValidator      (not in common list)
#   ✓ NumericPasswordValidator     (not fully numeric)
#   ✓ UserAttributeSimilarityValidator (no relation to test email/name)

STRONG_PASSWORD     = "X!9vQm2#rLpZ"
NEW_STRONG_PASSWORD = "N3w!P@ssXq92"


# ─── URL Constants — single source of truth ───────────────────────────────────
# All endpoint paths defined once.
# If a URL changes, update here — all tests update automatically.

REGISTER_URL             = "/api/accounts/register/"
LOGIN_URL                = "/api/accounts/login/"
LOGOUT_URL               = "/api/accounts/logout/"
REFRESH_URL              = "/api/accounts/token/refresh/"
VERIFY_EMAIL_URL         = "/api/accounts/verify-email/"
RESEND_VERIFICATION_URL  = "/api/accounts/resend-verification/"
PASSWORD_RESET_URL       = "/api/accounts/password-reset/"
PASSWORD_RESET_CONFIRM_URL = "/api/accounts/password-reset/confirm/"
CHANGE_PASSWORD_URL      = "/api/accounts/change-password/"
PROFILE_URL              = "/api/accounts/profile/"
AVATAR_UPLOAD_URL        = "/api/accounts/profile/avatar/"
ADDRESS_LIST_CREATE_URL  = "/api/accounts/addresses/"
ADDRESS_DETAIL_URL       = "/api/accounts/addresses/{pk}/"
ADDRESS_SET_DEFAULT_URL  = "/api/accounts/addresses/{pk}/set-default/"


# ─── Address Test Data ────────────────────────────────────────────────────────
# Valid city values from City choices.
# Used across address model tests and API tests.
# Province and postal code are auto-derived — never passed manually.

VALID_CITY_LAHORE    = "Lahore"      # → province: PB, postal: 54000
VALID_CITY_KARACHI   = "Karachi"     # → province: SD, postal: 75000
VALID_CITY_ISLAMABAD = "Islamabad"   # → province: IC, postal: 44000


# ─── User Fixtures ────────────────────────────────────────────────────────────

@pytest.fixture
def user(db) -> User:
    """
    Standard verified active customer.

    The baseline happy-path user for most tests.
    role=CUSTOMER, is_verified=True, is_active=True.
    """
    return User.objects.create_user(
        email="customer@test.com",
        full_name="Test Customer",
        password=STRONG_PASSWORD,
        is_verified=True,
    )


@pytest.fixture
def unverified_user(db) -> User:
    """
    Registered but email-unverified customer.

    Use for:
        - Login rejection before verification
        - Email verification flow tests
        - Resend verification tests
    """
    return User.objects.create_user(
        email="unverified@test.com",
        full_name="Unverified User",
        password=STRONG_PASSWORD,
        is_verified=False,
    )


@pytest.fixture
def inactive_user(db) -> User:
    """
    Verified but deactivated customer.

    Use for:
        - Login rejection for inactive accounts
        - Password reset enumeration prevention tests
    """
    return User.objects.create_user(
        email="inactive@test.com",
        full_name="Inactive User",
        password=STRONG_PASSWORD,
        is_verified=True,
        is_active=False,
    )


@pytest.fixture
def admin_user(db) -> User:
    """
    Django superuser with ADMIN role.

    Use for admin-only endpoint tests.
    role=ADMIN, is_verified=True, is_staff=True, is_superuser=True.
    """
    return User.objects.create_superuser(
        email="admin@test.com",
        full_name="Admin User",
        password=STRONG_PASSWORD,
    )


# ─── Authenticated Clients ────────────────────────────────────────────────────

@pytest.fixture
def auth_client(user: User) -> APIClient:
    """
    APIClient force-authenticated as the standard verified `user`.

    Why a separate instance — not the api_client fixture:
        If auth_client mutated the shared api_client instance,
        any test requesting BOTH fixtures would get an authenticated
        client for both — IsNotAuthenticated endpoints would
        incorrectly return 403 in those tests.

        Separate instance = complete isolation guaranteed.

    Usage:
        def test_something(self, auth_client, api_client):
            # auth_client  → authenticated as `user`
            # api_client   → completely unauthenticated, separate instance
    """
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def admin_client(admin_user: User) -> APIClient:
    """APIClient force-authenticated as admin_user."""
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


# ─── Token Factories ──────────────────────────────────────────────────────────

@pytest.fixture
def verification_token(unverified_user: User) -> EmailVerificationToken:
    """
    Fresh EmailVerificationToken for unverified_user.

    Replaces any existing tokens for this user (create_for_user deletes old ones).
    """
    return EmailVerificationToken.create_for_user(unverified_user)


@pytest.fixture
def password_reset_token(user: User) -> PasswordResetToken:
    """
    Fresh PasswordResetToken for verified user.

    Replaces any existing tokens for this user.
    """
    return PasswordResetToken.create_for_user(user)


# ─── Address Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def valid_address_payload() -> dict:
    """
    Minimal valid payload for address creation.

    Province, postal_code, country are auto-derived from city.
    They are never included in the request payload.

    City = Lahore → province = PB, postal_code = 54000, country = Pakistan
    """
    return {
        "label": "home",
        "address_line1": "123 Main Street",
        "address_line2": "Near Clock Tower",
        "city": VALID_CITY_LAHORE,
    }


@pytest.fixture
def user_address(user: User, valid_address_payload: dict) -> UserAddress:
    """
    Saved UserAddress instance belonging to `user`.

    Creates the address directly via model — no HTTP request.
    Use this when tests need an existing address to operate on
    (update, delete, set-default) without testing creation itself.
    """
    return UserAddress.objects.create(
        user=user,
        **valid_address_payload,
    )


@pytest.fixture
def default_address(user: User) -> UserAddress:
    """
    Saved UserAddress marked as default for `user`.

    Use for testing:
        - set-default replaces existing default
        - DB unique constraint on default
        - UserProfile.default_address property
    """
    return UserAddress.objects.create(
        user=user,
        label="home",
        address_line1="456 Default Street",
        city=VALID_CITY_KARACHI,
        is_default=True,
    )


# ─── Registration Payload ─────────────────────────────────────────────────────

@pytest.fixture
def valid_register_payload() -> dict:
    """
    Valid registration payload for a new user.

    Email is different from the `user` fixture email
    to avoid conflicts when both are used in the same test.
    """
    return {
        "full_name": "John Doe",
        "email": "john@example.com",
        "password": STRONG_PASSWORD,
        "confirm_password": STRONG_PASSWORD,
    }


# ─── Celery Task Mocks ────────────────────────────────────────────────────────
# autouse=True — applied to EVERY test in accounts test suite.
# Tests must never hit a real Celery broker.
# Tests that need to assert on call args receive the fixture explicitly:
#
#     def test_task_called(self, mock_verification_task):
#         assert mock_verification_task.called

@pytest.fixture(autouse=True)
def mock_verification_task(mocker):
    """
    Prevent send_verification_email_task from hitting Celery broker.

    Applied autouse=True so no test accidentally triggers a real email.
    """
    return mocker.patch(
        "apps.accounts.tasks.send_verification_email_task.delay"
    )


@pytest.fixture
def mock_welcome_task(mocker):
    """
    Mock welcome email task.

    NOT autouse — only needed in email verification tests.
    Tests that need it request it explicitly.
    """
    return mocker.patch(
        "apps.accounts.tasks.send_welcome_email_task.delay"
    )


@pytest.fixture
def mock_password_reset_task(mocker):
    """
    Mock password reset email task.

    NOT autouse — only needed in password reset tests.
    """
    return mocker.patch(
        "apps.accounts.tasks.send_password_reset_email_task.delay"
    )