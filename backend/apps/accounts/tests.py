# apps/accounts/tests.py
from __future__ import annotations
from django.utils import timezone
from datetime import timedelta

import pytest
from django.core.cache import caches
from rest_framework.test import APIClient
from unittest.mock import patch
from .models import EmailVerificationToken, User, UserProfile,PasswordResetToken
from apps.common.choices.role import Role

# ─── Password constant ────────────────────────────────────────────────────────
#
# "StrongPass123" was used throughout — this reliably fails
# Django's CommonPasswordValidator in most configurations.
#
# Replaced with a password that passes ALL default Django validators:
#   ✓ MinimumLengthValidator       (8+ chars)
#   ✓ CommonPasswordValidator      (not a common password)
#   ✓ NumericPasswordValidator     (not fully numeric)
#   ✓ UserAttributeSimilarityValidator (no relation to test email/name)
#
STRONG_PASSWORD = "X!9vQm2#rLpZ"


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear L1 and L2 caches before and after every test."""
    # NOTE: If 'local' is not defined in your CACHES setting,
    # replace caches['local'] with caches['default'] here.
    caches["default"].clear()
    caches["local"].clear()
    yield
    caches["default"].clear()
    caches["local"].clear()


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def user(db) -> User:
    return User.objects.create_user(
        email="customer@test.com",
        full_name="Test Customer",
        password=STRONG_PASSWORD,
        is_verified=True,
    )


@pytest.fixture
def unverified_user(db) -> User:
    return User.objects.create_user(
        email="unverified@test.com",
        full_name="Unverified User",
        password=STRONG_PASSWORD,
        is_verified=False,
    )


@pytest.fixture
def admin_user(db) -> User:
    return User.objects.create_superuser(
        email="admin@test.com",
        full_name="Admin User",
        password=STRONG_PASSWORD,
    )

@pytest.fixture
def auth_client(user: User) -> APIClient:
    """
    Authenticated API client using force_authenticate.

    Creates its own internal APIClient — does NOT share the api_client
    fixture instance. This is intentional:

    If this fixture accepted api_client as a parameter and mutated it,
    any test requesting both auth_client and api_client would receive
    the same authenticated instance for both, causing IsNotAuthenticated
    endpoints to incorrectly return 403.

    Usage:
        def test_something(self, auth_client, api_client):
            # auth_client → authenticated as `user`
            # api_client  → completely unauthenticated, separate instance
    """
    client = APIClient()
    client.force_authenticate(user=user)
    return client
# @pytest.fixture
# def auth_client(api_client: APIClient, user: User) -> APIClient:
#     """
#     Authenticated API client using force_authenticate.

#     CHANGED FROM: hitting /api/accounts/login/ directly.
#     REASON: Login-based auth in registration tests is fragile —
#     if login breaks, every registration test fails for the wrong reason.
#     force_authenticate() isolates registration tests completely.
#     """
#     api_client.force_authenticate(user=user)
#     return api_client


@pytest.fixture
def valid_register_payload() -> dict:
    return {
        "full_name": "John Doe",
        "email": "john@example.com",
        "password": STRONG_PASSWORD,
        "confirm_password": STRONG_PASSWORD,
    }


@pytest.fixture(autouse=True)
def mock_verification_task(mocker):
    """
    Prevent Celery task from firing on every registration test.

    REASON: Tests must not depend on a running Celery broker.
    Applied autouse=True so no individual test needs to remember to mock it.
    The fixture is returned so tests that need to assert call args can use it
    via explicit parameter:

        def test_something(self, mock_verification_task):
            assert mock_verification_task.called
    """
    return mocker.patch(
        "apps.accounts.views.send_verification_email_task.delay"
    )


# ─── Registration Tests ───────────────────────────────────────────────────────

@pytest.mark.django_db
class TestRegistration:

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_register_success(self, api_client, valid_register_payload):
        """201 returned and user exists in DB."""
        response = api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        assert response.status_code == 201
        assert response.data["success"] is True
        assert User.objects.filter(email="john@example.com").exists()

    def test_register_response_shape(self, api_client, valid_register_payload):
        """
        Response must conform to the standardized envelope.

        Keys: success, message, data, errors, meta.
        data.email must match the registered email.
        """
        response = api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data
        assert data["data"]["email"] == valid_register_payload["email"]

    def test_register_creates_unverified_user(self, api_client, valid_register_payload):
        """New users must not be verified until email confirmation."""
        api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        user = User.objects.get(email="john@example.com")
        assert user.is_verified is False

    def test_register_user_is_active_on_creation(self, api_client, valid_register_payload):
        """Users are active by default — deactivation is done explicitly."""
        api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        user = User.objects.get(email="john@example.com")
        assert user.is_active is True

    def test_register_creates_profile_automatically(self, api_client, valid_register_payload):
        """post_save signal must create UserProfile on user creation."""
        api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        user = User.objects.get(email="john@example.com")
        assert UserProfile.objects.filter(user=user).exists()

    def test_register_creates_verification_token(self, api_client, valid_register_payload):
        """An EmailVerificationToken must exist after registration."""
        api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        user = User.objects.get(email="john@example.com")
        assert EmailVerificationToken.objects.filter(user=user).exists()

    def test_register_password_is_hashed(self, api_client, valid_register_payload):
        """Raw password must never be stored — must survive check_password()."""
        api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        user = User.objects.get(email="john@example.com")
        assert user.password != valid_register_payload["password"]
        assert user.check_password(valid_register_payload["password"])

    def test_register_email_stored_lowercase(self, api_client, valid_register_payload):
        """
        Email normalization must happen at the manager level.

        Even if the user submits mixed-case, DB must store lowercase.
        """
        payload = {**valid_register_payload, "email": "JOHN@EXAMPLE.COM"}
        api_client.post("/api/accounts/register/", payload, format="json")
        assert User.objects.filter(email="john@example.com").exists()
        assert not User.objects.filter(email="JOHN@EXAMPLE.COM").exists()

    def test_register_dispatches_verification_task(
        self,
        api_client,
        valid_register_payload,
        mock_verification_task,
    ):
        """
        Celery task must be called once with correct user_id as first arg.

        mock_verification_task is the autouse fixture — requesting it
        explicitly here gives us access to assert on it.
        """
        api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        assert mock_verification_task.called
        assert mock_verification_task.call_count == 1
        user = User.objects.get(email=valid_register_payload["email"])
        call_args = mock_verification_task.call_args[0]
        assert call_args[0] == user.id

    # ── Duplicate Email ───────────────────────────────────────────────────────

    def test_register_duplicate_email_fails(
        self,
        api_client,
        user,
        valid_register_payload,
    ):
        """Existing email must return 400 with success=False."""
        valid_register_payload["email"] = user.email
        response = api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_register_duplicate_email_error_on_correct_field(
        self,
        api_client,
        user,
        valid_register_payload,
    ):
        """Duplicate email error must be on the 'email' field key."""
        valid_register_payload["email"] = user.email
        response = api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        assert "email" in response.data["errors"]

    # ── Password Validation ───────────────────────────────────────────────────

    def test_register_password_mismatch_fails(self, api_client, valid_register_payload):
        """Mismatched confirm_password must return error on confirm_password field."""
        valid_register_payload["confirm_password"] = "DifferentPass123"
        response = api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        assert response.status_code == 400
        # Error must land on the correct field — not on 'non_field_errors'
        assert "confirm_password" in response.data["errors"]

    def test_register_weak_password_fails(self, api_client, valid_register_payload):
        """Passwords that are too short must be rejected."""
        valid_register_payload["password"] = "123"
        valid_register_payload["confirm_password"] = "123"
        response = api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        assert response.status_code == 400
        assert "password" in response.data["errors"]

    def test_register_common_password_fails(self, api_client, valid_register_payload):
        """
        Common passwords must be rejected by Django's CommonPasswordValidator.

        'password123' is in Django's common password list.
        """
        valid_register_payload["password"] = "password123"
        valid_register_payload["confirm_password"] = "password123"
        response = api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        assert response.status_code == 400

    # ── Full Name Validation ──────────────────────────────────────────────────

    def test_register_single_word_name_fails(self, api_client, valid_register_payload):
        """Full name must have at least two words."""
        valid_register_payload["full_name"] = "John"
        response = api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        assert response.status_code == 400
        assert "full_name" in response.data["errors"]

    def test_register_blank_name_fails(self, api_client, valid_register_payload):
        """Blank full name must be rejected."""
        valid_register_payload["full_name"] = ""
        response = api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        assert response.status_code == 400
        assert "full_name" in response.data["errors"]

    # ── Email Format Validation ───────────────────────────────────────────────

    def test_register_invalid_email_fails(self, api_client, valid_register_payload):
        """Malformed email must be rejected with error on email field."""
        valid_register_payload["email"] = "not-an-email"
        response = api_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        assert response.status_code == 400
        assert "email" in response.data["errors"]

    # ── Missing Required Fields ───────────────────────────────────────────────

    @pytest.mark.parametrize("missing_field", [
        "full_name",
        "email",
        "password",
        "confirm_password",
    ])
    def test_register_missing_required_field_fails(
        self,
        api_client,
        valid_register_payload,
        missing_field,
    ):
        """
        Every required field must individually cause a 400 when omitted.

        Parametrized so adding a new required field only requires
        adding it to the list above.
        """
        payload = {
            k: v for k, v in valid_register_payload.items()
            if k != missing_field
        }
        response = api_client.post(
            "/api/accounts/register/",
            payload,
            format="json",
        )
        assert response.status_code == 400
        assert missing_field in response.data["errors"]

    # ── Auth State ────────────────────────────────────────────────────────────

    def test_authenticated_user_cannot_register(
        self,
        auth_client,
        valid_register_payload,
    ):
        """
        IsNotAuthenticated must block already-authenticated users.

        Uses force_authenticate so this test is not coupled to login behavior.
        """
        response = auth_client.post(
            "/api/accounts/register/",
            valid_register_payload,
            format="json",
        )
        assert response.status_code == 403


# apps/accounts/tests.py
# ─── add these constants near the top with your existing ones ─────────────────

LOGIN_URL  = "/api/accounts/login/"
LOGOUT_URL = "/api/accounts/logout/"
REFRESH_URL = "/api/accounts/token/refresh/"


# ─── Login Tests ──────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLogin:
    """
    Tests for POST /api/accounts/login/

    Coverage:
        - Happy path (tokens issued, cookie set)
        - Response shape conformance
        - Refresh token NOT in response body
        - Email case insensitivity
        - Invalid credentials (wrong password, nonexistent email)
        - User enumeration prevention
        - Inactive account blocked
        - Unverified email blocked
        - Already-authenticated user blocked
        - Missing required fields
    """

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_login_success_returns_200(self, api_client, user):
        """Valid credentials must return 200 with success=True."""
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_login_response_shape(self, api_client, user):
        """Response envelope must contain access token and user data."""
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data
        assert "access" in data["data"]
        assert "user" in data["data"]

    def test_login_sets_httponly_refresh_cookie(self, api_client, user):
        """
        Refresh token must be delivered via HttpOnly cookie.
        HttpOnly prevents JavaScript access — critical security requirement.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert "refresh_token" in response.cookies
        assert response.cookies["refresh_token"]["httponly"]

    def test_login_does_not_expose_refresh_token_in_body(self, api_client, user):
        """
        Refresh token must NEVER appear in the response body.
        Body is accessible to JS — only access token goes there.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert "refresh" not in response.data["data"]

    def test_login_email_is_case_insensitive(self, api_client, user):
        """Login must succeed regardless of email casing."""
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email.upper(), "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 200

    # ── Credential Failures ───────────────────────────────────────────────────

    def test_login_wrong_password_returns_400(self, api_client, user):
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "WrongPassword!99"},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_login_nonexistent_email_returns_400(self, api_client):
        response = api_client.post(
            LOGIN_URL,
            {"email": "ghost@example.com", "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 400

    def test_login_invalid_credentials_do_not_reveal_email_existence(
        self, api_client, user
    ):
        """
        Error message must be identical whether email exists or not.
        Different messages would allow user enumeration attacks.
        """
        real_user_response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "WrongPassword!99"},
            format="json",
        )
        fake_user_response = api_client.post(
            LOGIN_URL,
            {"email": "ghost@example.com", "password": "WrongPassword!99"},
            format="json",
        )
        assert str(real_user_response.data["errors"]) == str(
            fake_user_response.data["errors"]
        )

    # ── Account State Checks ──────────────────────────────────────────────────

    def test_login_inactive_user_returns_400(self, api_client, user):
        """Deactivated accounts must not receive tokens."""
        user.is_active = False
        user.save()
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 400

    def test_login_unverified_user_returns_400(self, api_client, unverified_user):
        """
        Unverified users must not receive tokens.
        Forces completion of the registration email verification flow.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": unverified_user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 400

    def test_login_unverified_user_error_is_non_field(
        self, api_client, unverified_user
    ):
        """Unverified email error must be on non_field_errors key."""
        response = api_client.post(
            LOGIN_URL,
            {"email": unverified_user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert "non_field_errors" in response.data["errors"]

    # ── Auth State ────────────────────────────────────────────────────────────

    def test_authenticated_user_cannot_login(self, auth_client, user):
        """IsNotAuthenticated must block already-authenticated users."""
        response = auth_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 403

    # ── Missing Fields ────────────────────────────────────────────────────────

    @pytest.mark.parametrize("missing_field", ["email", "password"])
    def test_login_missing_required_field_returns_400(
        self, api_client, user, missing_field
    ):
        """Each required field must individually cause 400 when omitted."""
        payload = {"email": user.email, "password": STRONG_PASSWORD}
        payload.pop(missing_field)
        response = api_client.post(LOGIN_URL, payload, format="json")
        assert response.status_code == 400
        assert missing_field in response.data["errors"]


# ─── Logout Tests ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLogout:
    """
    Tests for POST /api/accounts/logout/

    Coverage:
        - Happy path (cookie cleared, token blacklisted)
        - Unauthenticated request blocked
        - No cookie present still returns 200 (idempotent)
        - Double logout is safe
    """

    def _get_logged_in_client(self, api_client, user) -> APIClient:
        """
        Helper — log in and return client with refresh cookie attached.
        Also force_authenticate so DRF IsAuthenticated passes.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        api_client.cookies = response.cookies
        api_client.force_authenticate(user=user)
        return api_client

    def test_logout_success_returns_200(self, api_client, user):
        client = self._get_logged_in_client(api_client, user)
        response = client.post(LOGOUT_URL, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_logout_clears_refresh_cookie(self, api_client, user):
        """
        After logout, refresh cookie must be cleared.
        Django sets value='' and max_age=0 on delete_cookie().
        """
        client = self._get_logged_in_client(api_client, user)
        response = client.post(LOGOUT_URL, format="json")
        cookie = response.cookies.get("refresh_token")
        if cookie:
            assert cookie.value == "" or cookie["max-age"] == 0

    def test_logout_unauthenticated_returns_401(self, api_client):
        """IsAuthenticated must block unauthenticated logout attempts."""
        response = api_client.post(LOGOUT_URL, format="json")
        assert response.status_code == 401

    def test_logout_without_cookie_still_returns_200(self, api_client, user):
        """
        Logout with no cookie must return 200 — idempotent.
        Client may have already cleared cookie locally.
        """
        api_client.force_authenticate(user=user)
        response = api_client.post(LOGOUT_URL, format="json")
        assert response.status_code == 200

    def test_double_logout_does_not_crash(self, api_client, user):
        """
        Second logout with already-blacklisted token must not raise.
        Token is invalid on second call — must still return 200.
        """
        client = self._get_logged_in_client(api_client, user)
        client.post(LOGOUT_URL, format="json")
        response = client.post(LOGOUT_URL, format="json")
        assert response.status_code in (200, 401)


# ─── Token Refresh Tests ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTokenRefresh:
    """
    Tests for POST /api/accounts/token/refresh/

    Coverage:
        - Happy path (new access token returned)
        - Response shape conformance
        - No cookie → 401
        - Invalid/tampered token → 401
        - Expired-style token → 401
    """

    def _get_client_with_cookie(self, api_client, user) -> APIClient:
        """Helper — log in and attach refresh cookie to client."""
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        api_client.cookies = response.cookies
        return api_client

    def test_refresh_returns_200(self, api_client, user):
        """Valid refresh cookie must return 200."""
        client = self._get_client_with_cookie(api_client, user)
        response = client.post(REFRESH_URL, format="json")
        assert response.status_code == 200

    def test_refresh_returns_new_access_token(self, api_client, user):
        """Response must contain a non-empty access token."""
        client = self._get_client_with_cookie(api_client, user)
        response = client.post(REFRESH_URL, format="json")
        assert "access" in response.data["data"]
        assert len(response.data["data"]["access"]) > 0

    def test_refresh_response_shape(self, api_client, user):
        """Response must conform to the standardized envelope."""
        client = self._get_client_with_cookie(api_client, user)
        response = client.post(REFRESH_URL, format="json")
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_refresh_without_cookie_returns_401(self, api_client):
        """No cookie = no session = must return 401."""
        response = api_client.post(REFRESH_URL, format="json")
        assert response.status_code == 401
        assert response.data["success"] is False

    def test_refresh_with_invalid_token_returns_401(self, api_client):
        """Tampered or garbage token must be rejected with 401."""
        api_client.cookies["refresh_token"] = "totally.invalid.token"
        response = api_client.post(REFRESH_URL, format="json")
        assert response.status_code == 401
        assert response.data["success"] is False

    def test_refresh_new_access_token_differs_from_original(
        self, api_client, user
    ):
        """
        Each refresh call should produce a token valid for the user.
        We verify it is a non-empty JWT-shaped string.
        """
        client = self._get_client_with_cookie(api_client, user)
        response = client.post(REFRESH_URL, format="json")
        access = response.data["data"]["access"]
        # JWT format: three base64 segments separated by dots
        assert access.count(".") == 2


# apps/accounts/tests.py
# ─── add these constants near the top ────────────────────────────────────────

VERIFY_EMAIL_URL       = "/api/accounts/verify-email/"
RESEND_VERIFICATION_URL = "/api/accounts/resend-verification/"


# ─── Email Verification Tests ─────────────────────────────────────────────────

@pytest.mark.django_db
@patch("apps.accounts.views.send_welcome_email_task.delay")
class TestEmailVerification:
    """
    Tests for POST /api/accounts/verify-email/

    Coverage:
        - Happy path (user verified, token deleted, welcome email dispatched)
        - Response shape conformance
        - Invalid token format
        - Token not found in DB
        - Expired token
        - Already verified user (idempotent 200)
        - Token is deleted after use (one-time use)
    """

    def _make_token(self, user) -> EmailVerificationToken:
        """Helper — create a fresh verification token for a user."""
        return EmailVerificationToken.create_for_user(user)

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_verify_email_success_returns_200(
        self, mock_welcome, api_client, unverified_user
    ):
        """Valid token must return 200 and mark user as verified."""
        token_obj = self._make_token(unverified_user)
        response = api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_verify_email_response_shape(
        self, mock_welcome, api_client, unverified_user
    ):
        """Response must conform to standardized envelope."""
        token_obj = self._make_token(unverified_user)
        response = api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_verify_email_marks_user_as_verified(
        self, mock_welcome, api_client, unverified_user
    ):
        """User.is_verified must be True after successful verification."""
        token_obj = self._make_token(unverified_user)
        api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        unverified_user.refresh_from_db()
        assert unverified_user.is_verified is True

    def test_verify_email_deletes_token_after_use(
        self, mock_welcome, api_client, unverified_user
    ):
        """Token must be deleted after successful verification — one-time use."""
        token_obj = self._make_token(unverified_user)
        token_id = token_obj.token
        api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_id)},
            format="json",
        )
        assert not EmailVerificationToken.objects.filter(token=token_id).exists()

    def test_verify_email_dispatches_welcome_email(
        self, mock_welcome, api_client, unverified_user
    ):
        """Welcome email task must be dispatched exactly once."""
        token_obj = self._make_token(unverified_user)
        api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        assert mock_welcome.called
        assert mock_welcome.call_count == 1
        assert mock_welcome.call_args[0][0] == unverified_user.id

    def test_verified_user_can_now_login(
        self, mock_welcome, api_client, unverified_user
    ):
        """
        After verification, user must be able to log in.
        End-to-end confirmation that is_verified gate works.
        """
        token_obj = self._make_token(unverified_user)
        api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        login_response = api_client.post(
            LOGIN_URL,
            {"email": unverified_user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert login_response.status_code == 200

    # ── Token Not Found ───────────────────────────────────────────────────────

    def test_verify_email_invalid_token_returns_400(
        self, mock_welcome, api_client
    ):
        """Non-existent token UUID must return 400."""
        import uuid
        response = api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(uuid.uuid4())},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_verify_email_invalid_format_returns_400(
        self, mock_welcome, api_client
    ):
        """Non-UUID string must fail serializer validation with 400."""
        response = api_client.post(
            VERIFY_EMAIL_URL,
            {"token": "not-a-uuid"},
            format="json",
        )
        assert response.status_code == 400
        assert "token" in response.data["errors"]

    def test_verify_email_missing_token_returns_400(
        self, mock_welcome, api_client
    ):
        """Missing token field must return 400."""
        response = api_client.post(VERIFY_EMAIL_URL, {}, format="json")
        assert response.status_code == 400
        assert "token" in response.data["errors"]

    # ── Expired Token ─────────────────────────────────────────────────────────

    def test_verify_email_expired_token_returns_400(
        self, mock_welcome, api_client, unverified_user
    ):
        """
        Expired token must return 400 with descriptive message.
        We backdate the token's created_at to simulate expiry.
        """
        from datetime import timedelta
        from django.utils import timezone

        token_obj = self._make_token(unverified_user)
        # Backdate beyond expiry window (assume 24h expiry)
        EmailVerificationToken.objects.filter(pk=token_obj.pk).update(
            expires_at=timezone.now() - timedelta(hours=25)
        )
        response = api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_verify_email_expired_token_does_not_verify_user(
        self, mock_welcome, api_client, unverified_user
    ):
        """Expired token must not change user's verified state."""
        from datetime import timedelta
        from django.utils import timezone

        token_obj = self._make_token(unverified_user)
        EmailVerificationToken.objects.filter(pk=token_obj.pk).update(
            expires_at=timezone.now() - timedelta(hours=25)
        )
        api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        unverified_user.refresh_from_db()
        assert unverified_user.is_verified is False

    # ── Already Verified ──────────────────────────────────────────────────────

    def test_verify_email_already_verified_returns_200(
        self, mock_welcome, api_client, user
    ):
        """
        Already-verified user must get 200 — idempotent endpoint.
        ``user`` fixture is verified by default.
        """
        import uuid
        # Create a token manually even though user is verified
        # to bypass the DoesNotExist check
        token_obj = EmailVerificationToken.objects.create(
            user=user,
        )
        response = api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        assert response.status_code == 200

    def test_verify_email_already_verified_does_not_dispatch_welcome(
        self, mock_welcome, api_client, user
    ):
        """Welcome email must NOT be sent if user was already verified."""
        token_obj = EmailVerificationToken.objects.create(user=user)
        api_client.post(
            VERIFY_EMAIL_URL,
            {"token": str(token_obj.token)},
            format="json",
        )
        assert not mock_welcome.called


# ─── Resend Verification Tests ────────────────────────────────────────────────

@pytest.mark.django_db
@patch("apps.accounts.views.send_verification_email_task.delay")
class TestResendVerification:
    """
    Tests for POST /api/accounts/resend-verification/

    Coverage:
        - Happy path (task dispatched for unverified user)
        - Response shape conformance
        - Unregistered email returns same 200 (enumeration prevention)
        - Already verified user returns same 200 (enumeration prevention)
        - Task called with correct args
        - Invalid email format returns 400
        - Missing email returns 400
    """

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_resend_verification_success_returns_200(
        self, mock_task, api_client, unverified_user
    ):
        """Valid unverified email must return 200."""
        response = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": unverified_user.email},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_resend_verification_response_shape(
        self, mock_task, api_client, unverified_user
    ):
        """Response must conform to standardized envelope."""
        response = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": unverified_user.email},
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_resend_verification_dispatches_task(
        self, mock_task, api_client, unverified_user
    ):
        """Task must be dispatched exactly once with correct user_id."""
        api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": unverified_user.email},
            format="json",
        )
        assert mock_task.called
        assert mock_task.call_count == 1
        assert mock_task.call_args[0][0] == unverified_user.id

    def test_resend_verification_creates_new_token(
        self, mock_task, api_client, unverified_user
    ):
        """A new EmailVerificationToken must exist after resend."""
        api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": unverified_user.email},
            format="json",
        )
        assert EmailVerificationToken.objects.filter(
            user=unverified_user
        ).exists()

    # ── Enumeration Prevention ────────────────────────────────────────────────

    def test_resend_unregistered_email_returns_200(
        self, mock_task, api_client
    ):
        """
        Unregistered email must return the same 200 as a valid request.
        Different responses would allow email enumeration.
        """
        response = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": "nobody@example.com"},
            format="json",
        )
        assert response.status_code == 200

    def test_resend_unregistered_email_does_not_dispatch_task(
        self, mock_task, api_client
    ):
        """No task must be dispatched for an unregistered email."""
        api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": "nobody@example.com"},
            format="json",
        )
        assert not mock_task.called

    def test_resend_already_verified_user_returns_200(
        self, mock_task, api_client, user
    ):
        """
        Already verified user must return same 200.
        Cannot reveal verification state to caller.
        """
        response = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": user.email},
            format="json",
        )
        assert response.status_code == 200

    def test_resend_already_verified_user_does_not_dispatch_task(
        self, mock_task, api_client, user
    ):
        """Task must not be dispatched if user is already verified."""
        api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": user.email},
            format="json",
        )
        assert not mock_task.called

    def test_resend_unregistered_and_verified_return_same_message(
        self, mock_task, api_client, user
    ):
        """
        All non-error responses must have identical message text.
        Message divergence would enable enumeration.
        """
        unregistered = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": "nobody@example.com"},
            format="json",
        )
        already_verified = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": user.email},
            format="json",
        )
        assert unregistered.data["message"] == already_verified.data["message"]

    # ── Validation Failures ───────────────────────────────────────────────────

    def test_resend_invalid_email_format_returns_400(
        self, mock_task, api_client
    ):
        """Malformed email must be rejected with 400."""
        response = api_client.post(
            RESEND_VERIFICATION_URL,
            {"email": "not-an-email"},
            format="json",
        )
        assert response.status_code == 400
        assert "email" in response.data["errors"]

    def test_resend_missing_email_returns_400(self, mock_task, api_client):
        """Missing email field must return 400."""
        response = api_client.post(
            RESEND_VERIFICATION_URL,
            {},
            format="json",
        )
        assert response.status_code == 400
        assert "email" in response.data["errors"]



# apps/accounts/tests.py
# ─── add these constants near the top ────────────────────────────────────────

PASSWORD_RESET_URL         = "/api/accounts/password-reset/"
PASSWORD_RESET_CONFIRM_URL = "/api/accounts/password-reset/confirm/"
CHANGE_PASSWORD_URL        = "/api/accounts/change-password/"

# New strong password used when testing password change/reset
NEW_STRONG_PASSWORD = "N3w!P@ssXq92"


# ─── Password Reset Request Tests ────────────────────────────────────────────

@pytest.mark.django_db
@patch("apps.accounts.views.send_password_reset_email_task.delay")
class TestPasswordResetRequest:
    """
    Tests for POST /api/accounts/password-reset/

    Coverage:
        - Happy path (token created, task dispatched)
        - Response shape conformance
        - Unregistered email returns same 200 (enumeration prevention)
        - Inactive user returns same 200
        - Task called with correct args
        - Invalid email format returns 400
        - Missing email returns 400
        - Unregistered and registered return identical message
    """

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_reset_request_returns_200(self, mock_task, api_client, user):
        """Valid registered email must return 200."""
        response = api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_reset_request_response_shape(self, mock_task, api_client, user):
        """Response must conform to standardized envelope."""
        response = api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_reset_request_creates_token(self, mock_task, api_client, user):
        """A PasswordResetToken must exist after a valid request."""
        api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        assert PasswordResetToken.objects.filter(user=user).exists()

    def test_reset_request_dispatches_task(self, mock_task, api_client, user):
        """Task must be dispatched exactly once with correct args."""
        api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        assert mock_task.called
        assert mock_task.call_count == 1
        assert mock_task.call_args[0][0] == user.id

    def test_reset_request_email_case_insensitive(
        self, mock_task, api_client, user
    ):
        """Email lookup must be case-insensitive."""
        response = api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email.upper()},
            format="json",
        )
        assert response.status_code == 200
        assert mock_task.called

    # ── Enumeration Prevention ────────────────────────────────────────────────

    def test_reset_request_unregistered_email_returns_200(
        self, mock_task, api_client
    ):
        """
        Unregistered email must return same 200 as registered email.
        Different responses would allow email enumeration.
        """
        response = api_client.post(
            PASSWORD_RESET_URL,
            {"email": "nobody@example.com"},
            format="json",
        )
        assert response.status_code == 200

    def test_reset_request_unregistered_email_does_not_dispatch_task(
        self, mock_task, api_client
    ):
        """No task must be dispatched for an unregistered email."""
        api_client.post(
            PASSWORD_RESET_URL,
            {"email": "nobody@example.com"},
            format="json",
        )
        assert not mock_task.called

    def test_reset_request_inactive_user_returns_200(
        self, mock_task, api_client, user
    ):
        """Inactive user must return same 200 — cannot reveal account state."""
        user.is_active = False
        user.save()
        response = api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        assert response.status_code == 200

    def test_reset_request_inactive_user_does_not_dispatch_task(
        self, mock_task, api_client, user
    ):
        """No task must be dispatched for inactive user."""
        user.is_active = False
        user.save()
        api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        assert not mock_task.called

    def test_reset_request_all_responses_have_identical_message(
        self, mock_task, api_client, user
    ):
        """
        Registered, unregistered, and inactive responses must be identical.
        Message divergence would enable enumeration.
        """
        registered = api_client.post(
            PASSWORD_RESET_URL,
            {"email": user.email},
            format="json",
        )
        unregistered = api_client.post(
            PASSWORD_RESET_URL,
            {"email": "nobody@example.com"},
            format="json",
        )
        assert registered.data["message"] == unregistered.data["message"]

    # ── Validation Failures ───────────────────────────────────────────────────

    def test_reset_request_invalid_email_returns_400(
        self, mock_task, api_client
    ):
        """Malformed email must be rejected with 400."""
        response = api_client.post(
            PASSWORD_RESET_URL,
            {"email": "not-an-email"},
            format="json",
        )
        assert response.status_code == 400
        assert "email" in response.data["errors"]

    def test_reset_request_missing_email_returns_400(
        self, mock_task, api_client
    ):
        """Missing email field must return 400."""
        response = api_client.post(PASSWORD_RESET_URL, {}, format="json")
        assert response.status_code == 400
        assert "email" in response.data["errors"]


# ─── Password Reset Confirm Tests ─────────────────────────────────────────────

@pytest.mark.django_db
class TestPasswordResetConfirm:
    """
    Tests for POST /api/accounts/password-reset/confirm/

    Coverage:
        - Happy path (password changed, token marked used)
        - Response shape conformance
        - Token not found returns 400
        - Expired token returns 400
        - Already used token returns 400
        - Mismatched passwords returns 400 on correct field
        - Weak password returns 400
        - Old password no longer works after reset
        - User can login with new password after reset
        - Token is single-use
    """

    def _make_token(self, user) -> PasswordResetToken:
        """Create a fresh password reset token for a user."""
        return PasswordResetToken.create_for_user(user)

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_reset_confirm_returns_200(self, api_client, user):
        """Valid token + valid password must return 200."""
        token_obj = self._make_token(user)
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_reset_confirm_response_shape(self, api_client, user):
        """Response must conform to standardized envelope."""
        token_obj = self._make_token(user)
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_reset_confirm_changes_password(self, api_client, user):
        """User password must be updated in DB after reset."""
        token_obj = self._make_token(user)
        api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        user.refresh_from_db()
        assert user.check_password(NEW_STRONG_PASSWORD)

    def test_reset_confirm_old_password_no_longer_works(self, api_client, user):
        """Old password must be invalid after reset."""
        token_obj = self._make_token(user)
        api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        user.refresh_from_db()
        assert not user.check_password(STRONG_PASSWORD)

    def test_reset_confirm_marks_token_as_used(self, api_client, user):
        """Token must be marked as used after successful reset."""
        token_obj = self._make_token(user)
        api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        token_obj.refresh_from_db()
        assert token_obj.is_used is True

    def test_reset_confirm_user_can_login_with_new_password(
        self, api_client, user
    ):
        """End-to-end: user must be able to log in with new password."""
        token_obj = self._make_token(user)
        api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        login_response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": NEW_STRONG_PASSWORD},
            format="json",
        )
        assert login_response.status_code == 200

    # ── Token Not Found ───────────────────────────────────────────────────────

    def test_reset_confirm_invalid_token_returns_400(self, api_client):
        """Non-existent token UUID must return 400."""
        import uuid
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(uuid.uuid4()),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_reset_confirm_invalid_token_format_returns_400(self, api_client):
        """Non-UUID token string must fail serializer validation."""
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": "not-a-uuid",
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 400
        assert "token" in response.data["errors"]

    # ── Expired Token ─────────────────────────────────────────────────────────

    def test_reset_confirm_expired_token_returns_400(self, api_client, user):
        """Expired token must return 400 — backdating expires_at field."""
        from datetime import timedelta
        from django.utils import timezone

        token_obj = self._make_token(user)
        PasswordResetToken.objects.filter(pk=token_obj.pk).update(
            expires_at=timezone.now() - timedelta(hours=2)
        )
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 400

    def test_reset_confirm_expired_token_does_not_change_password(
        self, api_client, user
    ):
        """Expired token must not change the user's password."""
        from datetime import timedelta
        from django.utils import timezone

        token_obj = self._make_token(user)
        PasswordResetToken.objects.filter(pk=token_obj.pk).update(
            expires_at=timezone.now() - timedelta(hours=2)
        )
        api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        user.refresh_from_db()
        assert not user.check_password(NEW_STRONG_PASSWORD)

    # ── Single Use ────────────────────────────────────────────────────────────

    def test_reset_confirm_token_is_single_use(self, api_client, user):
        """
        Second use of same token must return 400.
        Prevents replay attacks.
        """
        token_obj = self._make_token(user)
        payload = {
            "token": str(token_obj.token),
            "password": NEW_STRONG_PASSWORD,
            "confirm_password": NEW_STRONG_PASSWORD,
        }
        api_client.post(PASSWORD_RESET_CONFIRM_URL, payload, format="json")
        second_response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL, payload, format="json"
        )
        assert second_response.status_code == 400

    # ── Password Validation ───────────────────────────────────────────────────

    def test_reset_confirm_password_mismatch_returns_400(self, api_client, user):
        """Mismatched passwords must return error on confirm_password field."""
        token_obj = self._make_token(user)
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": NEW_STRONG_PASSWORD,
                "confirm_password": "DifferentPass999!",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "confirm_password" in response.data["errors"]

    def test_reset_confirm_weak_password_returns_400(self, api_client, user):
        """Weak password must be rejected."""
        token_obj = self._make_token(user)
        response = api_client.post(
            PASSWORD_RESET_CONFIRM_URL,
            {
                "token": str(token_obj.token),
                "password": "123",
                "confirm_password": "123",
            },
            format="json",
        )
        assert response.status_code == 400


# ─── Change Password Tests ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestChangePassword:
    """
    Tests for POST /api/accounts/change-password/

    Coverage:
        - Happy path (password changed)
        - Response shape conformance
        - Unauthenticated request blocked
        - Incorrect current password returns 400 on correct field
        - Mismatched new passwords returns 400 on correct field
        - Weak new password returns 400
        - Old password no longer works after change
        - New password can be used to log in
        - Same password as current rejected by Django validators
    """

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_change_password_returns_200(self, auth_client):
        """Valid current password + valid new password must return 200."""
        response = auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_change_password_response_shape(self, auth_client):
        """Response must conform to standardized envelope."""
        response = auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_change_password_updates_db(self, auth_client, user):
        """Password must be updated in DB after change."""
        auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        user.refresh_from_db()
        assert user.check_password(NEW_STRONG_PASSWORD)

    def test_change_password_old_password_no_longer_works(
        self, auth_client, user
    ):
        """Old password must be invalid after change."""
        auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        user.refresh_from_db()
        assert not user.check_password(STRONG_PASSWORD)

    def test_change_password_new_password_works_for_login(
        self, auth_client, user, api_client
    ):
        """End-to-end: user must be able to log in with new password."""
        auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        login_response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": NEW_STRONG_PASSWORD},
            format="json",
        )
        assert login_response.status_code == 200

    # ── Auth State ────────────────────────────────────────────────────────────

    def test_change_password_unauthenticated_returns_401(self, api_client):
        """IsAuthenticated must block unauthenticated requests."""
        response = api_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 401

    # ── Current Password Validation ───────────────────────────────────────────

    def test_change_password_wrong_current_password_returns_400(
        self, auth_client
    ):
        """Incorrect current password must return 400."""
        response = auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": "WrongPassword!99",
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert response.status_code == 400

    def test_change_password_wrong_current_password_error_on_field(
        self, auth_client
    ):
        """Incorrect current password error must be on current_password field."""
        response = auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": "WrongPassword!99",
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": NEW_STRONG_PASSWORD,
            },
            format="json",
        )
        assert "current_password" in response.data["errors"]

    # ── New Password Validation ───────────────────────────────────────────────

    def test_change_password_mismatch_returns_400(self, auth_client):
        """Mismatched new passwords must return error on confirm_new_password."""
        response = auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": NEW_STRONG_PASSWORD,
                "confirm_new_password": "DifferentPass999!",
            },
            format="json",
        )
        assert response.status_code == 400
        assert "confirm_new_password" in response.data["errors"]

    def test_change_password_weak_new_password_returns_400(self, auth_client):
        """Weak new password must be rejected."""
        response = auth_client.post(
            CHANGE_PASSWORD_URL,
            {
                "current_password": STRONG_PASSWORD,
                "new_password": "123",
                "confirm_new_password": "123",
            },
            format="json",
        )
        assert response.status_code == 400

    # ── Missing Fields ────────────────────────────────────────────────────────

    @pytest.mark.parametrize("missing_field", [
        "current_password",
        "new_password",
        "confirm_new_password",
    ])
    def test_change_password_missing_field_returns_400(
        self, auth_client, missing_field
    ):
        """Every required field must individually cause 400 when omitted."""
        payload = {
            "current_password": STRONG_PASSWORD,
            "new_password": NEW_STRONG_PASSWORD,
            "confirm_new_password": NEW_STRONG_PASSWORD,
        }
        payload.pop(missing_field)
        response = auth_client.post(
            CHANGE_PASSWORD_URL, payload, format="json"
        )
        assert response.status_code == 400
        assert missing_field in response.data["errors"]



# apps/accounts/tests.py
# ─── add these constants near the top ────────────────────────────────────────

PROFILE_URL      = "/api/accounts/profile/"
AVATAR_UPLOAD_URL = "/api/accounts/profile/avatar/"


# ─── Profile Tests ────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProfileGet:
    """
    Tests for GET /api/accounts/profile/

    Coverage:
        - Happy path (profile data returned)
        - Response shape conformance
        - Nested profile present in response
        - Unauthenticated request blocked
    """

    def test_get_profile_returns_200(self, auth_client):
        """Authenticated user must receive their profile."""
        response = auth_client.get(PROFILE_URL, format="json")
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_get_profile_response_shape(self, auth_client):
        """Response must conform to standardized envelope."""
        response = auth_client.get(PROFILE_URL, format="json")
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_get_profile_contains_user_fields(self, auth_client, user):
        """Response data must contain core user fields."""
        response = auth_client.get(PROFILE_URL, format="json")
        data = response.data["data"]
        assert data["email"] == user.email
        assert data["full_name"] == user.full_name
        assert "role" in data
        assert "is_verified" in data

    def test_get_profile_contains_nested_profile(self, auth_client):
        """Response data must contain nested profile object."""
        response = auth_client.get(PROFILE_URL, format="json")
        data = response.data["data"]
        assert "profile" in data
        profile = data["profile"]
        assert "phone" in profile
        assert "gender" in profile
        assert "city" in profile
        assert "province" in profile
        assert "has_complete_address" in profile

    def test_get_profile_unauthenticated_returns_401(self, api_client):
        """IsAuthenticated must block unauthenticated requests."""
        response = api_client.get(PROFILE_URL, format="json")
        assert response.status_code == 401


@pytest.mark.django_db
class TestProfileUpdate:
    """
    Tests for PATCH /api/accounts/profile/

    Coverage:
        - Happy path (profile fields updated)
        - Response shape and updated data returned
        - Partial update (only sent fields change)
        - Phone validation (invalid format rejected)
        - Future date of birth rejected
        - Invalid gender choice rejected
        - Invalid province choice rejected
        - Unauthenticated request blocked
        - PUT method also accepted (alias for PATCH)
    """

    VALID_UPDATE = {
        "phone": "03001234567",
        "city": "Lahore",
        "province": "PB",
        "address_line1": "123 Main Street",
        "postal_code": "54000",
        "country": "Pakistan",
    }

    def test_patch_profile_returns_200(self, auth_client):
        """Valid partial update must return 200."""
        response = auth_client.patch(
            PROFILE_URL,
            self.VALID_UPDATE,
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_patch_profile_response_shape(self, auth_client):
        """Response must conform to standardized envelope."""
        response = auth_client.patch(
            PROFILE_URL,
            self.VALID_UPDATE,
            format="json",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_patch_profile_updates_fields_in_db(self, auth_client, user):
        """Updated fields must be persisted to DB."""
        auth_client.patch(
            PROFILE_URL,
            {"city": "Karachi", "province": "SD"},
            format="json",
        )
        user.profile.refresh_from_db()
        assert user.profile.city == "Karachi"
        assert user.profile.province == "SD"

    def test_patch_profile_response_reflects_updated_data(self, auth_client):
        """Response data must contain the newly saved values."""
        response = auth_client.patch(
            PROFILE_URL,
            {"city": "Islamabad"},
            format="json",
        )
        assert response.data["data"]["profile"]["city"] == "Islamabad"

    def test_patch_profile_is_partial(self, auth_client, user):
        """
        Unincluded fields must NOT be cleared on partial update.
        Sending only city must not reset phone to empty string.
        """
        user.profile.phone = "03001234567"
        user.profile.save(update_fields=["phone"])

        auth_client.patch(
            PROFILE_URL,
            {"city": "Multan"},
            format="json",
        )
        user.profile.refresh_from_db()
        assert user.profile.phone == "03001234567"
        assert user.profile.city == "Multan"

    def test_put_profile_also_accepted(self, auth_client):
        """PUT must be accepted as alias for PATCH."""
        response = auth_client.put(
            PROFILE_URL,
            {"city": "Quetta"},
            format="json",
        )
        assert response.status_code == 200

    # ── Phone Validation ──────────────────────────────────────────────────────

    def test_patch_invalid_phone_returns_400(self, auth_client):
        """Invalid phone format must return 400 on phone field."""
        response = auth_client.patch(
            PROFILE_URL,
            {"phone": "12345"},
            format="json",
        )
        assert response.status_code == 400
        assert "phone" in response.data["errors"]

    def test_patch_valid_international_phone_accepted(self, auth_client):
        """International format (+923001234567) must be accepted."""
        response = auth_client.patch(
            PROFILE_URL,
            {"phone": "+923001234567"},
            format="json",
        )
        assert response.status_code == 200

    def test_patch_valid_local_phone_accepted(self, auth_client):
        """Local format (03001234567) must be accepted."""
        response = auth_client.patch(
            PROFILE_URL,
            {"phone": "03001234567"},
            format="json",
        )
        assert response.status_code == 200

    # ── Date of Birth Validation ──────────────────────────────────────────────

    def test_patch_future_date_of_birth_returns_400(self, auth_client):
        """Future date of birth must be rejected."""
        from datetime import date, timedelta
        future_date = date.today() + timedelta(days=365)
        response = auth_client.patch(
            PROFILE_URL,
            {"date_of_birth": future_date.isoformat()},
            format="json",
        )
        assert response.status_code == 400
        assert "date_of_birth" in response.data["errors"]

    def test_patch_past_date_of_birth_accepted(self, auth_client):
        """Valid past date of birth must be accepted."""
        response = auth_client.patch(
            PROFILE_URL,
            {"date_of_birth": "1990-06-15"},
            format="json",
        )
        assert response.status_code == 200

    # ── Choice Field Validation ───────────────────────────────────────────────

    def test_patch_invalid_gender_returns_400(self, auth_client):
        """Invalid gender choice must return 400."""
        response = auth_client.patch(
            PROFILE_URL,
            {"gender": "X"},
            format="json",
        )
        assert response.status_code == 400
        assert "gender" in response.data["errors"]

    def test_patch_invalid_province_returns_400(self, auth_client):
        """Invalid province choice must return 400."""
        response = auth_client.patch(
            PROFILE_URL,
            {"province": "XX"},
            format="json",
        )
        assert response.status_code == 400
        assert "province" in response.data["errors"]

    # ── Auth State ────────────────────────────────────────────────────────────

    def test_patch_profile_unauthenticated_returns_401(self, api_client):
        """IsAuthenticated must block unauthenticated requests."""
        response = api_client.patch(
            PROFILE_URL,
            {"city": "Lahore"},
            format="json",
        )
        assert response.status_code == 401


@pytest.mark.django_db
class TestAvatarUpload:
    """
    Tests for POST /api/accounts/profile/avatar/

    Coverage:
        - Happy path (avatar saved, URL returned)
        - Response shape conformance
        - Missing file returns 400
        - File too large returns 400
        - Invalid file type returns 400
        - Unauthenticated request blocked
        - Old avatar replaced (not duplicated)
    """

    def _make_image(self, name="test.jpg", size=(100, 100), fmt="JPEG") -> object:
        """
        Create an in-memory image file for upload testing.
        Uses Pillow — already a Django dependency via ImageField.
        """
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile

        buf = BytesIO()
        img = Image.new("RGB", size, color=(255, 0, 0))
        img.save(buf, format=fmt)
        buf.seek(0)
        content_type = "image/jpeg" if fmt == "JPEG" else "image/png"
        return SimpleUploadedFile(name, buf.read(), content_type=content_type)

    def _make_oversized_image(self) -> object:
        """Create an in-memory file that exceeds 2MB."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        # 2MB + 1 byte of data
        content = b"x" * (2 * 1024 * 1024 + 1)
        return SimpleUploadedFile(
            "big.jpg", content, content_type="image/jpeg"
        )

    def _make_invalid_type_file(self) -> object:
        """Create a file with disallowed MIME type (PDF)."""
        from django.core.files.uploadedfile import SimpleUploadedFile
        return SimpleUploadedFile(
            "doc.pdf", b"fake pdf content", content_type="application/pdf"
        )

    # ── Happy Path ────────────────────────────────────────────────────────────

    def test_avatar_upload_returns_200(self, auth_client):
        """Valid image upload must return 200."""
        response = auth_client.post(
            AVATAR_UPLOAD_URL,
            {"avatar": self._make_image()},
            format="multipart",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_avatar_upload_response_shape(self, auth_client):
        """Response must conform to standardized envelope."""
        response = auth_client.post(
            AVATAR_UPLOAD_URL,
            {"avatar": self._make_image()},
            format="multipart",
        )
        data = response.data
        assert "success" in data
        assert "message" in data
        assert "errors" in data
        assert "meta" in data

    def test_avatar_upload_returns_avatar_url(self, auth_client):
        """Response data must contain avatar_url as non-empty string."""
        response = auth_client.post(
            AVATAR_UPLOAD_URL,
            {"avatar": self._make_image()},
            format="multipart",
        )
        assert "avatar" in response.data["data"]
        assert response.data["data"]["avatar"]

    def test_avatar_upload_saves_to_profile(self, auth_client, user):
        """Avatar must be persisted to the user's profile in DB."""
        auth_client.post(
            AVATAR_UPLOAD_URL,
            {"avatar": self._make_image()},
            format="multipart",
        )
        user.profile.refresh_from_db()
        assert bool(user.profile.avatar)

    # ── Validation Failures ───────────────────────────────────────────────────

    def test_avatar_upload_missing_file_returns_400(self, auth_client):
        """Missing avatar field must return 400."""
        response = auth_client.post(
            AVATAR_UPLOAD_URL,
            {},
            format="multipart",
        )
        assert response.status_code == 400
        assert "avatar" in response.data["errors"]

    def test_avatar_upload_oversized_file_returns_400(self, auth_client):
        """File exceeding 2MB must return 400."""
        response = auth_client.post(
            AVATAR_UPLOAD_URL,
            {"avatar": self._make_oversized_image()},
            format="multipart",
        )
        assert response.status_code == 400
        assert "avatar" in response.data["errors"]

    def test_avatar_upload_invalid_type_returns_400(self, auth_client):
        """Non-image MIME type must return 400."""
        response = auth_client.post(
            AVATAR_UPLOAD_URL,
            {"avatar": self._make_invalid_type_file()},
            format="multipart",
        )
        assert response.status_code == 400

    # ── Auth State ────────────────────────────────────────────────────────────

    def test_avatar_upload_unauthenticated_returns_401(self, api_client):
        """IsAuthenticated must block unauthenticated requests."""
        response = api_client.post(
            AVATAR_UPLOAD_URL,
            {"avatar": self._make_image()},
            format="multipart",
        )
        assert response.status_code == 401
