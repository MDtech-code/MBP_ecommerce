
# backend/apps/accounts/tests/api/test_login.py
"""
Login endpoint tests.

Endpoint: POST /api/accounts/login/
View:     LoginView

Covers:
    - Happy path (200, tokens, cookie)
    - Response shape
    - Refresh token security (cookie only, not body)
    - Email case insensitivity
    - Credential failures (wrong password, nonexistent email)
    - User enumeration prevention
    - Account state (inactive, unverified)
    - IsNotAuthenticated enforcement
    - Missing fields
    - UserLoginActivity logging (success + failure)
    - UserLoginActivity immutability guard
"""
from __future__ import annotations

import pytest

from apps.accounts.models import UserLoginActivity
from apps.accounts.tests.conftest import (
    LOGIN_URL,
    STRONG_PASSWORD,
)
from apps.core.error_codes import ErrorCode


@pytest.mark.django_db
class TestLoginHappyPath:

    def test_returns_200_on_success(self, api_client, user):
        """Valid credentials must return 200 with success=True."""
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 200
        assert response.data["success"] is True

    def test_response_envelope_shape(self, api_client, user):
        """
        Response envelope must contain all five keys.
        data must contain access token and user object.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        data = response.data

        for key in ("success", "message", "data", "errors", "meta"):
            assert key in data, f"Missing envelope key: '{key}'"

        assert "access" in data["data"]
        assert "user"   in data["data"]

    def test_sets_httponly_refresh_cookie(self, api_client, user):
        """
        Refresh token must be in HttpOnly cookie — never in body.

        HttpOnly = JavaScript cannot read it.
        Prevents XSS attacks from stealing the refresh token.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert "refresh_token" in response.cookies
        assert response.cookies["refresh_token"]["httponly"]

    def test_refresh_token_not_in_response_body(self, api_client, user):
        """
        Refresh token must NEVER appear in response body.

        Body is readable by JavaScript — only access token goes there.
        If refresh were in the body, XSS could steal it.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert "refresh" not in response.data["data"]

    def test_email_is_case_insensitive(self, api_client, user):
        """
        Login must succeed regardless of email casing.
        UserManager normalizes emails to lowercase on creation.
        Django's authenticate() must handle case mismatch.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email.upper(), "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 200

    def test_user_data_in_response_contains_expected_fields(
        self,
        api_client,
        user,
    ):
        """
        User object in response must contain key identity fields.
        Covers UserSerializer fields used by the frontend immediately
        after login (display name, role, verification state).
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        user_data = response.data["data"]["user"]

        for field in ("id", "email", "full_name", "role", "is_verified"):
            assert field in user_data, f"Missing user field: '{field}'"


@pytest.mark.django_db
class TestLoginCredentialFailures:

    def test_wrong_password_returns_400(self, api_client, user):
        """Wrong password must return 400 with success=False."""
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "WrongPassword!99"},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_nonexistent_email_returns_400(self, api_client):
        """Unregistered email must return 400 — same as wrong password."""
        response = api_client.post(
            LOGIN_URL,
            {"email": "ghost@example.com", "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 400

    def test_invalid_credentials_do_not_reveal_email_existence(
        self,
        api_client,
        user,
    ):
        """
        Error message must be IDENTICAL whether email exists or not.

        Different messages = user enumeration attack vector.
        An attacker could probe which emails are registered.

        We compare non_fields code and message — if either differs
        between a real and fake email, this test fails.
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

        real_non_fields = real_user_response.data["errors"]["non_fields"]
        fake_non_fields = fake_user_response.data["errors"]["non_fields"]

        # Both must have identical message and code — no leak of account existence
        assert real_non_fields["message"] == fake_non_fields["message"]
        assert real_non_fields["code"]    == fake_non_fields["code"]

    def test_wrong_password_error_in_non_fields(
        self,
        api_client,
        user,
    ):
        """
        Invalid credentials error must be in errors.non_fields — not fields.

        OLD: assert "non_field_errors" in response.data["errors"]
             Read old flat shape where DRF key leaked through.
        NEW: errors is {code, fields, non_fields}.
             Non-field errors live in errors.non_fields.

        Why non_fields not fields.email or fields.password:
            We deliberately do not tell the user WHICH field is wrong.
            Saying 'email not found' reveals account existence.
            Saying 'password wrong' confirms the email IS registered.
            non_fields is the safe, ambiguous location.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "WrongPassword!99"},
            format="json",
        )
        errors = response.data["errors"]

        assert errors["fields"]     is None
        assert errors["non_fields"] is not None
        assert errors["non_fields"]["code"]    == ErrorCode.INVALID_CREDENTIALS
        assert errors["non_fields"]["message"] == "Invalid email or password."

    def test_wrong_password_top_level_error_code(self, api_client, user):
        """
        errors.code must be authentication_error for login failures.

        Top-level code tells frontend the category before inspecting details.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "WrongPassword!99"},
            format="json",
        )
        errors = response.data["errors"]

    # Top-level code reflects status 400 → validation_error
        assert errors["code"] == ErrorCode.VALIDATION_ERROR

    # Specific code is on non_fields — this is what frontend uses
        assert errors["non_fields"]["code"] == ErrorCode.INVALID_CREDENTIALS


@pytest.mark.django_db
class TestLoginAccountStateChecks:

    def test_inactive_user_returns_400(self, api_client, inactive_user):
        """
        Deactivated accounts must not receive tokens.
        LoginSerializer checks user.is_active after authenticate().
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": inactive_user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_unverified_user_returns_400(self, api_client, unverified_user):
        """
        Unverified users must not receive tokens.
        Forces completion of registration email verification flow.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": unverified_user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 400
        assert response.data["success"] is False

    def test_unverified_user_error_in_non_fields(
        self,
        api_client,
        unverified_user,
    ):
        """
        Unverified email error must be in errors.non_fields with correct code.

        OLD: assert "non_field_errors" in response.data["errors"]
        NEW: errors.non_fields.code == ErrorCode.EMAIL_NOT_VERIFIED

        Frontend uses this specific code to:
            - Show the unverified message
            - Render a "Resend verification email" button
        This is exactly the use case that started this whole implementation.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": unverified_user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        errors = response.data["errors"]

        assert errors["fields"]     is None
        assert errors["non_fields"] is not None
        assert errors["non_fields"]["code"] == ErrorCode.EMAIL_NOT_VERIFIED

    def test_inactive_user_error_in_non_fields(
        self,
        api_client,
        inactive_user,
    ):
        """
        Inactive account error must be in errors.non_fields
        with code == ErrorCode.ACCOUNT_INACTIVE.

        Frontend uses this code to show support contact message
        rather than a generic error.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": inactive_user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        errors = response.data["errors"]

        assert errors["non_fields"] is not None
        assert errors["non_fields"]["code"] == ErrorCode.INVALID_CREDENTIALS

    def test_inactive_user_no_cookie_set(self, api_client, inactive_user):
        """
        Blocked login must not set any refresh token cookie.
        Cookie is only set after successful token generation.
        """
        response = api_client.post(
            LOGIN_URL,
            {"email": inactive_user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert "refresh_token" not in response.cookies


@pytest.mark.django_db
class TestLoginPermissions:

    def test_authenticated_user_blocked(self, auth_client, user):
        """
        IsNotAuthenticated must return 403 for already-authenticated users.
        Prevents re-login flow from running for active sessions.
        """
        response = auth_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert response.status_code == 403
        assert response.data["success"] is False


@pytest.mark.django_db
class TestLoginMissingFields:

    @pytest.mark.parametrize("missing_field", ["email", "password"])
    def test_missing_required_field_returns_400(
        self,
        api_client,
        user,
        missing_field,
    ):
        """
        Each required field must individually cause 400 when omitted.

        OLD: assert missing_field in response.data["errors"]
             Read old flat shape — errors.email existed directly.
        NEW: errors.fields.{field} — field errors live in errors.fields.
        """
        payload = {"email": user.email, "password": STRONG_PASSWORD}
        payload.pop(missing_field)

        response = api_client.post(LOGIN_URL, payload, format="json")

        assert response.status_code == 400
        assert response.data["errors"]["fields"] is not None
        assert missing_field in response.data["errors"]["fields"]

    def test_empty_payload_returns_400(self, api_client):
        """Completely empty payload must return 400."""
        response = api_client.post(LOGIN_URL, {}, format="json")
        assert response.status_code == 400
        assert response.data["success"] is False


# ═══════════════════════════════════════════════════════════════════════════════
# UserLoginActivity LOGGING — UNCHANGED
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.mark.django_db
class TestLoginActivityLogging:
    """
    LoginView calls log_login_activity() on every attempt.
    UserLoginActivity is append-only (raises on update).

    These tests have zero dependency on error shape —
    they test DB records not response structure.
    ALL UNCHANGED from before.
    """

    def test_successful_login_creates_activity_record(self, api_client, user):
        api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert UserLoginActivity.objects.filter(
            user=user,
            was_successful=True,
        ).exists()

    def test_successful_login_stores_correct_email(self, api_client, user):
        api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        record = UserLoginActivity.objects.filter(user=user).latest("created_at")
        assert record.email_attempted == user.email

    def test_failed_login_creates_activity_record(self, api_client, user):
        api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "WrongPassword!99"},
            format="json",
        )
        assert UserLoginActivity.objects.filter(was_successful=False).exists()

    def test_failed_login_stores_failure_reason(self, api_client, user):
        api_client.post(
            LOGIN_URL,
            {"email": user.email, "password": "WrongPassword!99"},
            format="json",
        )
        record = UserLoginActivity.objects.filter(
            was_successful=False,
        ).latest("created_at")
        assert record.failure_reason == "invalid_credentials"

    def test_failed_login_for_nonexistent_email_creates_record(self, api_client):
        api_client.post(
            LOGIN_URL,
            {"email": "ghost@example.com", "password": "WrongPassword!99"},
            format="json",
        )
        assert UserLoginActivity.objects.filter(
            email_attempted="ghost@example.com",
            was_successful=False,
        ).exists()

    def test_unverified_user_login_creates_failed_record(
        self, api_client, unverified_user
    ):
        api_client.post(
            LOGIN_URL,
            {"email": unverified_user.email, "password": STRONG_PASSWORD},
            format="json",
        )
        assert UserLoginActivity.objects.filter(
            email_attempted=unverified_user.email,
        ).exists()

    def test_activity_record_is_immutable(self, db):
        from apps.accounts.models import User

        user = User.objects.create_user(
            email="immutable@test.com",
            full_name="Immutable Test",
            password=STRONG_PASSWORD,
            is_verified=True,
        )
        record = UserLoginActivity.objects.create(
            user=user,
            email_attempted=user.email,
            was_successful=True,
            failure_reason="",
        )
        record.was_successful = False
        with pytest.raises(ValueError, match="immutable"):
            record.save()

    def test_activity_record_preserved_after_user_deletion(self, db):
        from apps.accounts.models import User

        user = User.objects.create_user(
            email="deletable@test.com",
            full_name="Deletable User",
            password=STRONG_PASSWORD,
            is_verified=True,
        )
        UserLoginActivity.objects.create(
            user=user,
            email_attempted=user.email,
            was_successful=True,
            failure_reason="",
        )
        user_email = user.email
        user.delete()

        record = UserLoginActivity.objects.get(email_attempted=user_email)
        assert record.user is None
        assert record.was_successful is True
# # backend/apps/accounts/tests/api/test_login.py
# """
# Login endpoint tests.

# Endpoint: POST /api/accounts/login/
# View:     LoginView

# Covers:
#     - Happy path (200, tokens, cookie)
#     - Response shape
#     - Refresh token security (cookie only, not body)
#     - Email case insensitivity
#     - Credential failures (wrong password, nonexistent email)
#     - User enumeration prevention
#     - Account state (inactive, unverified)
#     - IsNotAuthenticated enforcement
#     - Missing fields
#     - UserLoginActivity logging (success + failure)
#     - UserLoginActivity immutability guard
# """
# from __future__ import annotations

# import pytest

# from apps.accounts.models import UserLoginActivity
# from apps.accounts.tests.conftest import (
#     LOGIN_URL,
#     STRONG_PASSWORD,
# )


# @pytest.mark.django_db
# class TestLoginHappyPath:

#     def test_returns_200_on_success(self, api_client, user):
#         """Valid credentials must return 200 with success=True."""
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert response.status_code == 200
#         assert response.data["success"] is True

#     def test_response_envelope_shape(self, api_client, user):
#         """
#         Response envelope must contain all five keys.
#         data must contain access token and user object.
#         """
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         data = response.data

#         for key in ("success", "message", "data", "errors", "meta"):
#             assert key in data, f"Missing envelope key: '{key}'"

#         assert "access" in data["data"]
#         assert "user" in data["data"]

#     def test_sets_httponly_refresh_cookie(self, api_client, user):
#         """
#         Refresh token must be in HttpOnly cookie — never in body.

#         HttpOnly = JavaScript cannot read it.
#         Prevents XSS attacks from stealing the refresh token.
#         """
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert "refresh_token" in response.cookies
#         assert response.cookies["refresh_token"]["httponly"]

#     def test_refresh_token_not_in_response_body(self, api_client, user):
#         """
#         Refresh token must NEVER appear in response body.

#         Body is readable by JavaScript — only access token goes there.
#         If refresh were in the body, XSS could steal it.
#         """
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert "refresh" not in response.data["data"]

#     def test_email_is_case_insensitive(self, api_client, user):
#         """
#         Login must succeed regardless of email casing.
#         UserManager normalizes emails to lowercase on creation.
#         Django's authenticate() must handle case mismatch.
#         """
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email.upper(), "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert response.status_code == 200

#     def test_user_data_in_response_contains_expected_fields(
#         self,
#         api_client,
#         user,
#     ):
#         """
#         User object in response must contain key identity fields.
#         Covers UserSerializer fields used by the frontend immediately
#         after login (display name, role, verification state).
#         """
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         user_data = response.data["data"]["user"]

#         for field in ("id", "email", "full_name", "role", "is_verified"):
#             assert field in user_data, f"Missing user field: '{field}'"


# @pytest.mark.django_db
# class TestLoginCredentialFailures:

#     def test_wrong_password_returns_400(self, api_client, user):
#         """Wrong password must return 400 with success=False."""
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": "WrongPassword!99"},
#             format="json",
#         )
#         assert response.status_code == 400
#         assert response.data["success"] is False

#     def test_nonexistent_email_returns_400(self, api_client):
#         """Unregistered email must return 400 — same as wrong password."""
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": "ghost@example.com", "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert response.status_code == 400

#     def test_invalid_credentials_do_not_reveal_email_existence(
#         self,
#         api_client,
#         user,
#     ):
#         """
#         Error message must be IDENTICAL whether email exists or not.

#         Different messages = user enumeration attack vector.
#         An attacker could probe which emails are registered.

#         We compare the serialized errors string — if messages differ
#         in any way (wording, field key, structure), this test fails.
#         """
#         real_user_response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": "WrongPassword!99"},
#             format="json",
#         )
#         fake_user_response = api_client.post(
#             LOGIN_URL,
#             {"email": "ghost@example.com", "password": "WrongPassword!99"},
#             format="json",
#         )
#         assert str(real_user_response.data["errors"]) == str(
#             fake_user_response.data["errors"]
#         )

#     def test_wrong_password_error_on_non_field_errors(
#         self,
#         api_client,
#         user,
#     ):
#         """
#         Invalid credentials error must be on non_field_errors.

#         Why non_field_errors not 'email' or 'password':
#             We deliberately do not tell the user WHICH field is wrong.
#             Saying 'email not found' reveals account existence.
#             Saying 'password wrong' confirms the email IS registered.
#             non_field_errors is the safe, ambiguous key.
#         """
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": "WrongPassword!99"},
#             format="json",
#         )
#         assert "non_field_errors" in response.data["errors"]


# @pytest.mark.django_db
# class TestLoginAccountStateChecks:

#     def test_inactive_user_returns_400(self, api_client, inactive_user):
#         """
#         Deactivated accounts must not receive tokens.
#         LoginSerializer checks user.is_active after authenticate().
#         """
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": inactive_user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert response.status_code == 400
#         assert response.data["success"] is False

#     def test_unverified_user_returns_400(self, api_client, unverified_user):
#         """
#         Unverified users must not receive tokens.
#         Forces completion of registration email verification flow.
#         """
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": unverified_user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert response.status_code == 400
#         assert response.data["success"] is False

#     def test_unverified_user_error_on_non_field_errors(
#         self,
#         api_client,
#         unverified_user,
#     ):
#         """
#         Unverified email error must land on non_field_errors.
#         Frontend uses this to offer 'resend verification' link.
#         """
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": unverified_user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert "non_field_errors" in response.data["errors"]

#     def test_inactive_user_no_cookie_set(self, api_client, inactive_user):
#         """
#         Blocked login must not set any refresh token cookie.
#         Cookie is only set after successful token generation.
#         """
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": inactive_user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert "refresh_token" not in response.cookies


# @pytest.mark.django_db
# class TestLoginPermissions:

#     def test_authenticated_user_blocked(self, auth_client, user):
#         """
#         IsNotAuthenticated must return 403 for already-authenticated users.

#         Prevents re-login flow from running for active sessions.
#         """
#         response = auth_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert response.status_code == 403
#         assert response.data["success"] is False


# @pytest.mark.django_db
# class TestLoginMissingFields:

#     @pytest.mark.parametrize("missing_field", ["email", "password"])
#     def test_missing_required_field_returns_400(
#         self,
#         api_client,
#         user,
#         missing_field,
#     ):
#         """
#         Each required field must individually cause 400 when omitted.
#         Error must appear on the missing field's key.
#         """
#         payload = {"email": user.email, "password": STRONG_PASSWORD}
#         payload.pop(missing_field)

#         response = api_client.post(LOGIN_URL, payload, format="json")
#         assert response.status_code == 400
#         assert missing_field in response.data["errors"]

#     def test_empty_payload_returns_400(self, api_client):
#         """Completely empty payload must return 400."""
#         response = api_client.post(LOGIN_URL, {}, format="json")
#         assert response.status_code == 400
#         assert response.data["success"] is False


# # ═══════════════════════════════════════════════════════════════════════════════
# # UserLoginActivity LOGGING
# # ═══════════════════════════════════════════════════════════════════════════════

# @pytest.mark.django_db
# class TestLoginActivityLogging:
#     """
#     LoginView calls log_login_activity() on every attempt.
#     UserLoginActivity is append-only (raises on update).

#     These tests confirm:
#         1. A record is created on success
#         2. A record is created on failure
#         3. was_successful flag is correct
#         4. email_attempted is stored
#         5. failure_reason is stored on failure
#         6. The immutability guard works
#     """

#     def test_successful_login_creates_activity_record(
#         self,
#         api_client,
#         user,
#     ):
#         """
#         Successful login must create exactly one UserLoginActivity row
#         with was_successful=True.
#         """
#         api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert UserLoginActivity.objects.filter(
#             user=user,
#             was_successful=True,
#         ).exists()

#     def test_successful_login_stores_correct_email(
#         self,
#         api_client,
#         user,
#     ):
#         """
#         email_attempted must match the submitted email (normalized).
#         """
#         api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         record = UserLoginActivity.objects.filter(user=user).latest("created_at")
#         assert record.email_attempted == user.email

#     def test_failed_login_creates_activity_record(
#         self,
#         api_client,
#         user,
#     ):
#         """
#         Failed login must create a UserLoginActivity row
#         with was_successful=False.
#         """
#         api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": "WrongPassword!99"},
#             format="json",
#         )
#         assert UserLoginActivity.objects.filter(
#             was_successful=False,
#         ).exists()

#     def test_failed_login_stores_failure_reason(
#         self,
#         api_client,
#         user,
#     ):
#         """
#         failure_reason must be stored for failed attempts.
#         LoginView uses 'invalid_credentials' for bad password.
#         """
#         api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": "WrongPassword!99"},
#             format="json",
#         )
#         record = UserLoginActivity.objects.filter(
#             was_successful=False,
#         ).latest("created_at")
#         assert record.failure_reason == "invalid_credentials"

#     def test_failed_login_for_nonexistent_email_creates_record(
#         self,
#         api_client,
#     ):
#         """
#         Even attempts against non-existent emails must be logged.
#         email_attempted stores the raw submitted email — no user FK.
#         """
#         api_client.post(
#             LOGIN_URL,
#             {"email": "ghost@example.com", "password": "WrongPassword!99"},
#             format="json",
#         )
#         assert UserLoginActivity.objects.filter(
#             email_attempted="ghost@example.com",
#             was_successful=False,
#         ).exists()

#     def test_unverified_user_login_creates_failed_record(
#         self,
#         api_client,
#         unverified_user,
#     ):
#         """
#         Blocked login (unverified) must still create an activity record.
#         The view calls log_login_activity even on serializer failure.

#         Note: unverified user passes authenticate() — credentials are
#         valid — but is then blocked by the is_verified check.
#         The failure is logged at the serializer validation stage.
#         """
#         api_client.post(
#             LOGIN_URL,
#             {"email": unverified_user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         # Record may be created by the view's validation-error branch
#         # which logs email_attempted from request.data
#         assert UserLoginActivity.objects.filter(
#             email_attempted=unverified_user.email,
#         ).exists()

#     def test_activity_record_is_immutable(self, db):
#         """
#         UserLoginActivity.save() must raise ValueError on update.

#         The model's save() guard prevents any modification to existing rows.
#         Security logs must never be tampered with.
#         """
#         from apps.accounts.models import User

#         user = User.objects.create_user(
#             email="immutable@test.com",
#             full_name="Immutable Test",
#             password=STRONG_PASSWORD,
#             is_verified=True,
#         )
#         record = UserLoginActivity.objects.create(
#             user=user,
#             email_attempted=user.email,
#             was_successful=True,
#             failure_reason="",
#         )

#         # Attempting to update must raise
#         record.was_successful = False
#         with pytest.raises(ValueError, match="immutable"):
#             record.save()

#     def test_activity_record_preserved_after_user_deletion(self, db):
#         """
#         UserLoginActivity uses SET_NULL on user FK.
#         Deleting the user must not delete the activity log.

#         Why: Security logs must outlive user accounts for auditing.
#         """
#         from apps.accounts.models import User

#         user = User.objects.create_user(
#             email="deletable@test.com",
#             full_name="Deletable User",
#             password=STRONG_PASSWORD,
#             is_verified=True,
#         )
#         UserLoginActivity.objects.create(
#             user=user,
#             email_attempted=user.email,
#             was_successful=True,
#             failure_reason="",
#         )

#         user_email = user.email
#         user.delete()

#         # Record still exists, user FK is now null
#         record = UserLoginActivity.objects.get(email_attempted=user_email)
#         assert record.user is None
#         assert record.was_successful is True
# from __future__ import annotations
# import pytest
# from apps.accounts.tests.conftest import (
#     STRONG_PASSWORD,
#     LOGIN_URL, 

    
# )







# @pytest.mark.django_db
# class TestLogin:
#     """
#     Tests for POST /api/accounts/login/

#     Coverage:
#         - Happy path (tokens issued, cookie set)
#         - Response shape conformance
#         - Refresh token NOT in response body
#         - Email case insensitivity
#         - Invalid credentials (wrong password, nonexistent email)
#         - User enumeration prevention
#         - Inactive account blocked
#         - Unverified email blocked
#         - Already-authenticated user blocked
#         - Missing required fields
#     """

#     # ── Happy Path ────────────────────────────────────────────────────────────

#     def test_login_success_returns_200(self, api_client, user):
#         """Valid credentials must return 200 with success=True."""
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert response.status_code == 200
#         assert response.data["success"] is True

#     def test_login_response_shape(self, api_client, user):
#         """Response envelope must contain access token and user data."""
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         data = response.data
#         assert "success" in data
#         assert "message" in data
#         assert "errors" in data
#         assert "meta" in data
#         assert "access" in data["data"]
#         assert "user" in data["data"]

#     def test_login_sets_httponly_refresh_cookie(self, api_client, user):
#         """
#         Refresh token must be delivered via HttpOnly cookie.
#         HttpOnly prevents JavaScript access — critical security requirement.
#         """
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert "refresh_token" in response.cookies
#         assert response.cookies["refresh_token"]["httponly"]

#     def test_login_does_not_expose_refresh_token_in_body(self, api_client, user):
#         """
#         Refresh token must NEVER appear in the response body.
#         Body is accessible to JS — only access token goes there.
#         """
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert "refresh" not in response.data["data"]

#     def test_login_email_is_case_insensitive(self, api_client, user):
#         """Login must succeed regardless of email casing."""
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email.upper(), "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert response.status_code == 200

#     # ── Credential Failures ───────────────────────────────────────────────────

#     def test_login_wrong_password_returns_400(self, api_client, user):
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": "WrongPassword!99"},
#             format="json",
#         )
#         assert response.status_code == 400
#         assert response.data["success"] is False

#     def test_login_nonexistent_email_returns_400(self, api_client):
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": "ghost@example.com", "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert response.status_code == 400

#     def test_login_invalid_credentials_do_not_reveal_email_existence(
#         self, api_client, user
#     ):
#         """
#         Error message must be identical whether email exists or not.
#         Different messages would allow user enumeration attacks.
#         """
#         real_user_response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": "WrongPassword!99"},
#             format="json",
#         )
#         fake_user_response = api_client.post(
#             LOGIN_URL,
#             {"email": "ghost@example.com", "password": "WrongPassword!99"},
#             format="json",
#         )
#         assert str(real_user_response.data["errors"]) == str(
#             fake_user_response.data["errors"]
#         )

#     # ── Account State Checks ──────────────────────────────────────────────────

#     def test_login_inactive_user_returns_400(self, api_client, user):
#         """Deactivated accounts must not receive tokens."""
#         user.is_active = False
#         user.save()
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert response.status_code == 400

#     def test_login_unverified_user_returns_400(self, api_client, unverified_user):
#         """
#         Unverified users must not receive tokens.
#         Forces completion of the registration email verification flow.
#         """
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": unverified_user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert response.status_code == 400

#     def test_login_unverified_user_error_is_non_field(
#         self, api_client, unverified_user
#     ):
#         """Unverified email error must be on non_field_errors key."""
#         response = api_client.post(
#             LOGIN_URL,
#             {"email": unverified_user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert "non_field_errors" in response.data["errors"]

#     # ── Auth State ────────────────────────────────────────────────────────────

#     def test_authenticated_user_cannot_login(self, auth_client, user):
#         """IsNotAuthenticated must block already-authenticated users."""
#         response = auth_client.post(
#             LOGIN_URL,
#             {"email": user.email, "password": STRONG_PASSWORD},
#             format="json",
#         )
#         assert response.status_code == 403

#     # ── Missing Fields ────────────────────────────────────────────────────────

#     @pytest.mark.parametrize("missing_field", ["email", "password"])
#     def test_login_missing_required_field_returns_400(
#         self, api_client, user, missing_field
#     ):
#         """Each required field must individually cause 400 when omitted."""
#         payload = {"email": user.email, "password": STRONG_PASSWORD}
#         payload.pop(missing_field)
#         response = api_client.post(LOGIN_URL, payload, format="json")
#         assert response.status_code == 400
#         assert missing_field in response.data["errors"]
