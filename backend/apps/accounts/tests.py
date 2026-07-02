# apps/accounts/tests.py
from __future__ import annotations
from django.utils import timezone
from datetime import timedelta

import pytest
from django.core.cache import caches
from rest_framework.test import APIClient

from .models import EmailVerificationToken, User, UserProfile
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
def auth_client(api_client: APIClient, user: User) -> APIClient:
    """
    Authenticated API client using force_authenticate.

    CHANGED FROM: hitting /api/accounts/login/ directly.
    REASON: Login-based auth in registration tests is fragile —
    if login breaks, every registration test fails for the wrong reason.
    force_authenticate() isolates registration tests completely.
    """
    api_client.force_authenticate(user=user)
    return api_client


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

# ─── Email Verification Tests ───────────────────────────────────────────────

@pytest.mark.django_db
class TestEmailVerification:

    def test_verify_email_success(self, api_client, unverified_user):
        token_obj = EmailVerificationToken.create_for_user(unverified_user)
        response = api_client.post("/api/accounts/verify-email/", {
            "token": str(token_obj.token)
        }, format='json')
        assert response.status_code == 200
        unverified_user.refresh_from_db()
        assert unverified_user.is_verified is True

    def test_verify_email_deletes_token(self, api_client, unverified_user):
        token_obj = EmailVerificationToken.create_for_user(unverified_user)
        api_client.post("/api/accounts/verify-email/", {
            "token": str(token_obj.token)
        }, format='json')
        assert not EmailVerificationToken.objects.filter(id=token_obj.id).exists()

    def test_verify_email_invalid_token_fails(self, api_client):
        response = api_client.post("/api/accounts/verify-email/", {
            "token": "00000000-0000-0000-0000-000000000000"
        }, format='json')
        assert response.status_code == 400

    def test_verify_email_expired_token_fails(self, api_client, unverified_user):
        token_obj = EmailVerificationToken.create_for_user(unverified_user)
        token_obj.expires_at = timezone.now() - timedelta(hours=1)
        token_obj.save()

        response = api_client.post("/api/accounts/verify-email/", {
            "token": str(token_obj.token)
        }, format='json')
        assert response.status_code == 400

    def test_verify_already_verified_user_returns_success(self, api_client, user):
        token_obj = EmailVerificationToken.create_for_user(user)
        response = api_client.post("/api/accounts/verify-email/", {
            "token": str(token_obj.token)
        }, format='json')
        assert response.status_code == 200


@pytest.mark.django_db
class TestResendVerification:

    def test_resend_verification_for_unverified_user(self, api_client, unverified_user):
        response = api_client.post("/api/accounts/resend-verification/", {
            "email": unverified_user.email
        }, format='json')
        assert response.status_code == 200
        assert EmailVerificationToken.objects.filter(user=unverified_user).exists()

    def test_resend_verification_nonexistent_email_returns_success(self, api_client):
        """Should not reveal if email exists — security best practice."""
        response = api_client.post("/api/accounts/resend-verification/", {
            "email": "doesnotexist@test.com"
        }, format='json')
        assert response.status_code == 200

    def test_resend_verification_already_verified_no_token_created(self, api_client, user):
        EmailVerificationToken.objects.filter(user=user).delete()
        api_client.post("/api/accounts/resend-verification/", {
            "email": user.email
        }, format='json')
        assert not EmailVerificationToken.objects.filter(user=user).exists()

'''

# ─── Login Tests ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLogin:

    def test_login_success(self, api_client, user):
        response = api_client.post("/api/accounts/login/", {
            "email": user.email,
            "password": "StrongPass123",
        }, format='json')
        assert response.status_code == 200
        assert "access" in response.data["data"]

    def test_login_sets_refresh_cookie(self, api_client, user):
        response = api_client.post("/api/accounts/login/", {
            "email": user.email,
            "password": "StrongPass123",
        }, format='json')
        assert "refresh_token" in response.cookies

    def test_login_wrong_password_fails(self, api_client, user):
        response = api_client.post("/api/accounts/login/", {
            "email": user.email,
            "password": "WrongPassword",
        }, format='json')
        assert response.status_code == 400

    def test_login_nonexistent_email_fails(self, api_client):
        response = api_client.post("/api/accounts/login/", {
            "email": "noone@test.com",
            "password": "anything",
        }, format='json')
        assert response.status_code == 400

    def test_login_inactive_user_fails(self, api_client, user):
        user.is_active = False
        user.save()
        response = api_client.post("/api/accounts/login/", {
            "email": user.email,
            "password": "StrongPass123",
        }, format='json')
        assert response.status_code == 400

    def test_authenticated_user_cannot_login_again(self, auth_client):
        response = auth_client.post("/api/accounts/login/", {
            "email": "customer@test.com",
            "password": "StrongPass123",
        }, format='json')
        assert response.status_code == 403


# ─── Logout Tests ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestLogout:

    def test_logout_success(self, auth_client):
        response = auth_client.post("/api/accounts/logout/")
        assert response.status_code == 200

    def test_logout_clears_refresh_cookie(self, auth_client):
        response = auth_client.post("/api/accounts/logout/")
        assert response.cookies["refresh_token"].value == ""

    def test_logout_unauthenticated_fails(self, api_client):
        response = api_client.post("/api/accounts/logout/")
        assert response.status_code == 401


# ─── Token Refresh Tests ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestTokenRefresh:

    def test_refresh_with_valid_cookie(self, api_client, user):
        login_response = api_client.post("/api/accounts/login/", {
            "email": user.email,
            "password": "StrongPass123",
        }, format='json')
        refresh_cookie = login_response.cookies["refresh_token"].value
        api_client.cookies["refresh_token"] = refresh_cookie

        response = api_client.post("/api/accounts/token/refresh/")
        assert response.status_code == 200
        assert "access" in response.data["data"]

    def test_refresh_without_cookie_fails(self, api_client):
        response = api_client.post("/api/accounts/token/refresh/")
        assert response.status_code == 401

    def test_refresh_with_invalid_token_fails(self, api_client):
        api_client.cookies["refresh_token"] = "invalid-token-value"
        response = api_client.post("/api/accounts/token/refresh/")
        assert response.status_code == 401


# ─── Password Reset Tests ─────────────────────────────────────────────────────

@pytest.mark.django_db
class TestPasswordReset:

    def test_password_reset_request_success(self, api_client, user):
        response = api_client.post("/api/accounts/password-reset/", {
            "email": user.email
        }, format='json')
        assert response.status_code == 200
        assert PasswordResetToken.objects.filter(user=user).exists()

    def test_password_reset_nonexistent_email_returns_success(self, api_client):
        response = api_client.post("/api/accounts/password-reset/", {
            "email": "noone@test.com"
        }, format='json')
        assert response.status_code == 200

    def test_password_reset_confirm_success(self, api_client, user):
        token_obj = PasswordResetToken.create_for_user(user)
        response = api_client.post("/api/accounts/password-reset/confirm/", {
            "token": str(token_obj.token),
            "password": "NewStrongPass123",
            "confirm_password": "NewStrongPass123",
        }, format='json')
        assert response.status_code == 200

        user.refresh_from_db()
        assert user.check_password("NewStrongPass123")

    def test_password_reset_confirm_marks_token_used(self, api_client, user):
        token_obj = PasswordResetToken.create_for_user(user)
        api_client.post("/api/accounts/password-reset/confirm/", {
            "token": str(token_obj.token),
            "password": "NewStrongPass123",
            "confirm_password": "NewStrongPass123",
        }, format='json')
        token_obj.refresh_from_db()
        assert token_obj.is_used is True

    def test_password_reset_confirm_token_reuse_fails(self, api_client, user):
        token_obj = PasswordResetToken.create_for_user(user)
        api_client.post("/api/accounts/password-reset/confirm/", {
            "token": str(token_obj.token),
            "password": "NewStrongPass123",
            "confirm_password": "NewStrongPass123",
        }, format='json')

        # try using same token again
        response = api_client.post("/api/accounts/password-reset/confirm/", {
            "token": str(token_obj.token),
            "password": "AnotherPass123",
            "confirm_password": "AnotherPass123",
        }, format='json')
        assert response.status_code == 400

    def test_password_reset_confirm_expired_token_fails(self, api_client, user):
        token_obj = PasswordResetToken.create_for_user(user)
        token_obj.expires_at = timezone.now() - timedelta(hours=2)
        token_obj.save()

        response = api_client.post("/api/accounts/password-reset/confirm/", {
            "token": str(token_obj.token),
            "password": "NewStrongPass123",
            "confirm_password": "NewStrongPass123",
        }, format='json')
        assert response.status_code == 400

    def test_password_reset_confirm_mismatch_fails(self, api_client, user):
        token_obj = PasswordResetToken.create_for_user(user)
        response = api_client.post("/api/accounts/password-reset/confirm/", {
            "token": str(token_obj.token),
            "password": "NewStrongPass123",
            "confirm_password": "DifferentPass123",
        }, format='json')
        assert response.status_code == 400


# ─── Change Password Tests ────────────────────────────────────────────────────

@pytest.mark.django_db
class TestChangePassword:

    def test_change_password_success(self, auth_client, user):
        response = auth_client.post("/api/accounts/change-password/", {
            "current_password": "StrongPass123",
            "new_password": "NewerPass123",
            "confirm_new_password": "NewerPass123",
        }, format='json')
        assert response.status_code == 200

        user.refresh_from_db()
        assert user.check_password("NewerPass123")

    def test_change_password_wrong_current_fails(self, auth_client):
        response = auth_client.post("/api/accounts/change-password/", {
            "current_password": "WrongPassword",
            "new_password": "NewerPass123",
            "confirm_new_password": "NewerPass123",
        }, format='json')
        assert response.status_code == 400

    def test_change_password_mismatch_fails(self, auth_client):
        response = auth_client.post("/api/accounts/change-password/", {
            "current_password": "StrongPass123",
            "new_password": "NewerPass123",
            "confirm_new_password": "DifferentPass123",
        }, format='json')
        assert response.status_code == 400

    def test_change_password_unauthenticated_fails(self, api_client):
        response = api_client.post("/api/accounts/change-password/", {
            "current_password": "StrongPass123",
            "new_password": "NewerPass123",
            "confirm_new_password": "NewerPass123",
        }, format='json')
        assert response.status_code == 401


# ─── Profile Tests ─────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestProfile:

    def test_get_profile_success(self, auth_client, user):
        response = auth_client.get("/api/accounts/profile/")
        assert response.status_code == 200
        assert response.data["data"]["email"] == user.email

    def test_get_profile_unauthenticated_fails(self, api_client):
        response = api_client.get("/api/accounts/profile/")
        assert response.status_code == 401

    def test_update_profile_success(self, auth_client):
        response = auth_client.put("/api/accounts/profile/", {
            "phone": "03001234567",
            "city": "Lahore",
            "province": "PB",
        }, format='json')
        assert response.status_code == 200

    def test_update_profile_invalid_phone_fails(self, auth_client):
        response = auth_client.put("/api/accounts/profile/", {
            "phone": "12345",
        }, format='json')
        assert response.status_code == 400

    def test_update_profile_persists_data(self, auth_client, user):
        auth_client.put("/api/accounts/profile/", {
            "city": "Karachi",
        }, format='json')
        user.profile.refresh_from_db()
        assert user.profile.city == "Karachi"


# ─── Avatar Upload Tests ──────────────────────────────────────────────────────

@pytest.mark.django_db
class TestAvatarUpload:

    def test_avatar_upload_unauthenticated_fails(self, api_client):
        response = api_client.post("/api/accounts/profile/avatar/")
        assert response.status_code == 401

    def test_avatar_upload_no_file_fails(self, auth_client):
        response = auth_client.post("/api/accounts/profile/avatar/", {}, format='multipart')
        assert response.status_code == 400


# ─── Model Tests ───────────────────────────────────────────────────────────────

@pytest.mark.django_db
class TestUserModel:

    def test_user_str_returns_email(self, user):
        assert str(user) == user.email

    def test_user_is_customer_property(self, user):
        assert user.is_customer is True
        assert user.is_admin is False

    def test_admin_is_admin_property(self, admin_user):
        assert admin_user.is_admin is True
        assert admin_user.role == Role.ADMIN

    def test_short_name_property(self, user):
        assert user.short_name == "Test"

    def test_create_user_without_email_fails(self):
        with pytest.raises(ValueError):
            User.objects.create_user(
                email="", full_name="No Email", password="pass"
            )

    def test_create_superuser_forces_admin_role(self, admin_user):
        assert admin_user.role == Role.ADMIN
        assert admin_user.is_staff is True
        assert admin_user.is_superuser is True
        assert admin_user.is_verified is True


@pytest.mark.django_db
class TestUserProfileModel:

    def test_profile_created_automatically(self, user):
        assert hasattr(user, "profile")
        assert isinstance(user.profile, UserProfile)

    def test_has_complete_address_false_by_default(self, user):
        assert user.profile.has_complete_address is False

    def test_has_complete_address_true_when_filled(self, user):
        profile = user.profile
        profile.address_line1 = "123 Main St"
        profile.city = "Lahore"
        profile.province = "PB"
        profile.postal_code = "54000"
        profile.save()
        assert profile.has_complete_address is True


@pytest.mark.django_db
class TestEmailVerificationTokenModel:

    def test_token_expires_in_24_hours(self, user):
        token = EmailVerificationToken.create_for_user(user)
        expected = token.created_at + timedelta(hours=24)
        assert abs((token.expires_at - expected).total_seconds()) < 5

    def test_create_for_user_deletes_old_tokens(self, user):
        token1 = EmailVerificationToken.create_for_user(user)
        token2 = EmailVerificationToken.create_for_user(user)
        assert not EmailVerificationToken.objects.filter(id=token1.id).exists()
        assert EmailVerificationToken.objects.filter(id=token2.id).exists()

    def test_is_expired_property(self, user):
        token = EmailVerificationToken.create_for_user(user)
        token.expires_at = timezone.now() - timedelta(hours=1)
        token.save()
        assert token.is_expired is True


@pytest.mark.django_db
class TestPasswordResetTokenModel:

    def test_token_expires_in_1_hour(self, user):
        token = PasswordResetToken.create_for_user(user)
        expected = token.created_at + timedelta(hours=1)
        assert abs((token.expires_at - expected).total_seconds()) < 5

    def test_is_valid_false_when_used(self, user):
        token = PasswordResetToken.create_for_user(user)
        token.mark_used()
        assert token.is_valid is False

    def test_is_valid_true_when_fresh(self, user):
        token = PasswordResetToken.create_for_user(user)
        assert token.is_valid is True


'''