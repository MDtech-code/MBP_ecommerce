# backend/apps/core/tests/test_permissions.py
"""
Tests for apps.core.permissions — centralized permission classes.

Every endpoint in the backend uses these permission classes.
If IsAdmin breaks, admin endpoints are either open to everyone
or locked to everyone — both are catastrophic.

Test structure:

    Layer 1 — Unit tests (direct has_permission() calls)
        No DB. No HTTP. Fast.
        Mock request and view objects.
        Tests the logic of each permission class in isolation.

    Layer 2 — Integration tests (full HTTP stack)
        Uses test views from conftest.py.
        Proves permissions are correctly applied in real requests.

Permission classes under test:
    IsAdmin                  — ADMIN role only
    IsAdminOrReadOnly        — read=anyone, write=ADMIN only
    IsCustomer               — CUSTOMER role + is_verified=True
    IsVerified               — is_verified=True, any role
    IsNotAuthenticated       — unauthenticated users only
    RoleBasedProfilePermission — verified + CUSTOMER or ADMIN
"""
from __future__ import annotations

import pytest
from django.test import override_settings
from rest_framework.test import APIRequestFactory

from apps.common.choices.role import Role
from apps.core.permissions import (
    IsAdmin,
    IsAdminOrReadOnly,
    IsCustomer,
    IsNotAuthenticated,
    IsVerified,
    RoleBasedProfilePermission,
)
from .conftest import test_urlpatterns

# ─── URL override for integration tests ───────────────────────────────────────

urlpatterns = test_urlpatterns


# ─── Unit test helpers ────────────────────────────────────────────────────────

def _make_request(method: str = "GET", user=None):
    """
    Build a minimal DRF request for direct permission testing.

    Why APIRequestFactory:
        Permission classes receive DRF Request objects.
        Plain Django RequestFactory produces HttpRequest objects
        which lack .user and .auth attributes — causing AttributeError
        inside permission classes.

    Args:
        method : HTTP method string
        user   : User instance to attach, or None for AnonymousUser
    """
    factory = APIRequestFactory()
    raw = getattr(factory, method.lower())("/test/")

    from rest_framework.request import Request
    from rest_framework.parsers import JSONParser
    request = Request(raw, parsers=[JSONParser()])

    if user is not None:
        request._user = user
        request._force_auth_user = user
    else:
        from django.contrib.auth.models import AnonymousUser
        request._user = AnonymousUser()

    return request


def _make_view():
    """Minimal view instance — permission classes only need it to exist."""
    from apps.core.api.views import BaseAPIView
    return BaseAPIView()


# ─── IsAdmin ──────────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestIsAdmin:
    """
    IsAdmin — allows access only to users with Role.ADMIN.

    Used for: admin dashboards, user management, system config.
    """

    def test_admin_user_is_allowed(self, plain_admin):
        """User with ADMIN role must be granted access."""
        request = _make_request(user=plain_admin)
        perm = IsAdmin()
        assert perm.has_permission(request, _make_view()) is True

    def test_customer_user_is_denied(self, plain_user):
        """User with CUSTOMER role must be denied."""
        request = _make_request(user=plain_user)
        perm = IsAdmin()
        assert perm.has_permission(request, _make_view()) is False

    def test_anonymous_user_is_denied(self):
        """Unauthenticated user must be denied."""
        request = _make_request(user=None)
        perm = IsAdmin()
        assert perm.has_permission(request, _make_view()) is False

    def test_user_without_role_attribute_is_denied(self):
        """
        User with no role attribute must be denied gracefully.

        getattr(request.user, 'role', None) must not raise AttributeError.
        Handles edge cases like custom auth backends.
        """
        from unittest.mock import MagicMock
        mock_user = MagicMock(spec=[])  # spec=[] means NO attributes
        request = _make_request(user=mock_user)
        perm = IsAdmin()
        # Must not raise
        result = perm.has_permission(request, _make_view())
        assert result is False

    def test_admin_permission_message(self):
        """Permission message must be set for frontend display."""
        perm = IsAdmin()
        assert perm.message == "You must be an admin to perform this action."


# ─── IsAdminOrReadOnly ────────────────────────────────────────────────────────

@pytest.mark.unit
class TestIsAdminOrReadOnly:
    """
    IsAdminOrReadOnly — read=anyone, write=ADMIN only.

    Used for: product listings (anyone views), product creation (admin only).
    """

    # ── Read methods — allowed for everyone ───────────────────────────────────

    @pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
    def test_read_methods_allowed_for_anonymous(self, method):
        """GET/HEAD/OPTIONS must be allowed for unauthenticated users."""
        request = _make_request(method=method, user=None)
        perm = IsAdminOrReadOnly()
        assert perm.has_permission(request, _make_view()) is True

    @pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
    def test_read_methods_allowed_for_customer(self, method, plain_user):
        """GET/HEAD/OPTIONS must be allowed for customer users."""
        request = _make_request(method=method, user=plain_user)
        perm = IsAdminOrReadOnly()
        assert perm.has_permission(request, _make_view()) is True

    @pytest.mark.parametrize("method", ["GET", "HEAD", "OPTIONS"])
    def test_read_methods_allowed_for_admin(self, method, plain_admin):
        """GET/HEAD/OPTIONS must be allowed for admin users."""
        request = _make_request(method=method, user=plain_admin)
        perm = IsAdminOrReadOnly()
        assert perm.has_permission(request, _make_view()) is True

    # ── Write methods — admin only ────────────────────────────────────────────

    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
    def test_write_methods_allowed_for_admin(self, method, plain_admin):
        """POST/PUT/PATCH/DELETE must be allowed for admin users."""
        request = _make_request(method=method, user=plain_admin)
        perm = IsAdminOrReadOnly()
        assert perm.has_permission(request, _make_view()) is True

    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
    def test_write_methods_denied_for_customer(self, method, plain_user):
        """POST/PUT/PATCH/DELETE must be denied for customer users."""
        request = _make_request(method=method, user=plain_user)
        perm = IsAdminOrReadOnly()
        assert perm.has_permission(request, _make_view()) is False

    @pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
    def test_write_methods_denied_for_anonymous(self, method):
        """POST/PUT/PATCH/DELETE must be denied for anonymous users."""
        request = _make_request(method=method, user=None)
        perm = IsAdminOrReadOnly()
        assert perm.has_permission(request, _make_view()) is False


# ─── IsCustomer ───────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestIsCustomer:
    """
    IsCustomer — CUSTOMER role + is_verified=True required.

    Both conditions must be true simultaneously.
    Verified admin, unverified customer, and anonymous all denied.
    """

    def test_verified_customer_is_allowed(self, plain_user):
        """
        Verified customer must be allowed.

        plain_user fixture: role=CUSTOMER, is_verified=True.
        """
        request = _make_request(user=plain_user)
        perm = IsCustomer()
        assert perm.has_permission(request, _make_view()) is True

    def test_unverified_customer_is_denied(self, plain_unverified_user):
        """
        Unverified customer must be denied.

        Both conditions required: role=CUSTOMER AND is_verified=True.
        Missing verification means denied even with correct role.
        """
        request = _make_request(user=plain_unverified_user)
        perm = IsCustomer()
        assert perm.has_permission(request, _make_view()) is False

    def test_verified_admin_is_denied(self, plain_admin):
        """
        Verified admin must be denied by IsCustomer.

        IsCustomer is specifically for customers.
        Admin endpoints have their own IsAdmin permission.
        """
        request = _make_request(user=plain_admin)
        perm = IsCustomer()
        assert perm.has_permission(request, _make_view()) is False

    def test_anonymous_user_is_denied(self):
        """Anonymous user must be denied."""
        request = _make_request(user=None)
        perm = IsCustomer()
        assert perm.has_permission(request, _make_view()) is False

    def test_permission_message_set(self):
        """Permission message must be set for frontend display."""
        perm = IsCustomer()
        assert "verified customer" in perm.message.lower()


# ─── IsVerified ───────────────────────────────────────────────────────────────

@pytest.mark.unit
class TestIsVerified:
    """
    IsVerified — is_verified=True required, any role accepted.

    Used for: endpoints available to both customers and admins
    as long as their email is verified.
    """

    def test_verified_user_is_allowed(self, plain_user):
        """Verified user (any role) must be allowed."""
        request = _make_request(user=plain_user)
        perm = IsVerified()
        assert perm.has_permission(request, _make_view()) is True

    def test_verified_admin_is_allowed(self, plain_admin):
        """Verified admin must also be allowed."""
        request = _make_request(user=plain_admin)
        perm = IsVerified()
        assert perm.has_permission(request, _make_view()) is True

    def test_unverified_user_is_denied(self, plain_unverified_user):
        """Unverified user must be denied regardless of role."""
        request = _make_request(user=plain_unverified_user)
        perm = IsVerified()
        assert perm.has_permission(request, _make_view()) is False

    def test_anonymous_user_is_denied(self):
        """
        Anonymous user must be denied.

        AnonymousUser has no is_verified attribute.
        getattr(request.user, 'is_verified', False) must return False.
        """
        request = _make_request(user=None)
        perm = IsVerified()
        assert perm.has_permission(request, _make_view()) is False

    def test_user_without_is_verified_attribute_denied(self):
        """
        User with no is_verified attribute must be denied gracefully.

        bool(getattr(user, 'is_verified', False)) must not raise.
        """
        from unittest.mock import MagicMock
        mock_user = MagicMock(spec=[])
        request = _make_request(user=mock_user)
        perm = IsVerified()
        result = perm.has_permission(request, _make_view())
        assert result is False

    def test_permission_message_set(self):
        """Permission message must mention verification."""
        perm = IsVerified()
        assert "verified" in perm.message.lower()


# ─── IsNotAuthenticated ───────────────────────────────────────────────────────

@pytest.mark.unit
class TestIsNotAuthenticated:
    """
    IsNotAuthenticated — allows ONLY unauthenticated users.

    Used for: registration, login, password reset request.
    Authenticated users hitting these endpoints get 403.
    """

    def test_anonymous_user_is_allowed(self):
        """Unauthenticated user must be allowed."""
        request = _make_request(user=None)
        perm = IsNotAuthenticated()
        assert perm.has_permission(request, _make_view()) is True

    def test_authenticated_customer_is_denied(self, plain_user):
        """
        Authenticated customer must be denied.

        Logged-in user hitting /register/ or /login/ makes no sense.
        IsNotAuthenticated blocks this correctly.
        """
        request = _make_request(user=plain_user)
        perm = IsNotAuthenticated()
        assert perm.has_permission(request, _make_view()) is False

    def test_authenticated_admin_is_denied(self, plain_admin):
        """Authenticated admin must also be denied."""
        request = _make_request(user=plain_admin)
        perm = IsNotAuthenticated()
        assert perm.has_permission(request, _make_view()) is False

    def test_user_with_is_authenticated_false_is_allowed(self):
        """
        User object with is_authenticated=False must be allowed.

        Handles custom auth backends that return user-like objects
        with is_authenticated=False instead of AnonymousUser.
        """
        from unittest.mock import MagicMock
        mock_user = MagicMock()
        mock_user.is_authenticated = False
        request = _make_request(user=mock_user)
        perm = IsNotAuthenticated()
        assert perm.has_permission(request, _make_view()) is True


# ─── RoleBasedProfilePermission ───────────────────────────────────────────────

@pytest.mark.unit
class TestRoleBasedProfilePermission:
    """
    RoleBasedProfilePermission — verified + (CUSTOMER or ADMIN).

    Rules:
        Not verified → denied (regardless of role)
        Verified + CUSTOMER → allowed
        Verified + ADMIN → allowed
        Verified + unknown role → denied
        Anonymous → denied
    """

    def test_verified_customer_is_allowed(self, plain_user):
        """Verified customer must be allowed."""
        request = _make_request(user=plain_user)
        perm = RoleBasedProfilePermission()
        assert perm.has_permission(request, _make_view()) is True

    def test_verified_admin_is_allowed(self, plain_admin):
        """Verified admin must be allowed."""
        request = _make_request(user=plain_admin)
        perm = RoleBasedProfilePermission()
        assert perm.has_permission(request, _make_view()) is True

    def test_unverified_customer_is_denied(self, plain_unverified_user):
        """
        Unverified customer must be denied.

        Verification check happens BEFORE role check.
        """
        request = _make_request(user=plain_unverified_user)
        perm = RoleBasedProfilePermission()
        assert perm.has_permission(request, _make_view()) is False

    def test_anonymous_user_is_denied(self):
        """Anonymous user must be denied."""
        request = _make_request(user=None)
        perm = RoleBasedProfilePermission()
        assert perm.has_permission(request, _make_view()) is False

    def test_verified_user_with_unknown_role_is_denied(self, db):
        """
        Verified user with unrecognized role must be denied.

        The permission only allows CUSTOMER and ADMIN.
        Any other role falls through to the final logger.warning + return False.
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user = User.objects.create_user(
            email="unknownrole@test.com",
            full_name="Unknown Role",
            password="X!9vQm2#rLpZ",
            is_verified=True,
        )
        # Force an unrecognized role value
        user.role = "MYSTERY_ROLE"
        request = _make_request(user=user)
        perm = RoleBasedProfilePermission()
        assert perm.has_permission(request, _make_view()) is False

    def test_permission_message_set(self):
        """Permission message must be set."""
        perm = RoleBasedProfilePermission()
        assert len(perm.message) > 0


# ─── Integration Tests ────────────────────────────────────────────────────────

@pytest.mark.integration
@pytest.mark.django_db
class TestPermissionsHTTPIntegration:
    """
    Integration tests — permissions via full HTTP stack.

    Uses test views from conftest.py.
    Proves each permission class is correctly wired to its view
    and returns the correct HTTP status code.
    """

    @override_settings(ROOT_URLCONF=__name__)
    def test_admin_view_allows_admin(self, api_client, plain_admin):
        """Admin view must return 200 for admin user."""
        api_client.force_authenticate(user=plain_admin)
        response = api_client.get("/test/admin/")
        assert response.status_code == 200

    @override_settings(ROOT_URLCONF=__name__)
    def test_admin_view_denies_customer(self, api_client, plain_user):
        """Admin view must return 403 for customer user."""
        api_client.force_authenticate(user=plain_user)
        response = api_client.get("/test/admin/")
        assert response.status_code == 403

    @override_settings(ROOT_URLCONF=__name__)
    def test_admin_view_denies_anonymous(self, api_client):
        """Admin view must return 403 for anonymous user."""
        response = api_client.get("/test/admin/")
        assert response.status_code in (401, 403)

    @override_settings(ROOT_URLCONF=__name__)
    def test_admin_or_read_only_get_allowed_anonymous(self, api_client):
        """GET on admin-or-read-only view must be allowed for anonymous."""
        response = api_client.get("/test/admin-or-read/")
        assert response.status_code == 200

    @override_settings(ROOT_URLCONF=__name__)
    def test_admin_or_read_only_post_denied_anonymous(self, api_client):
        """POST on admin-or-read-only view must be denied for anonymous."""
        response = api_client.post("/test/admin-or-read/", {}, format="json")
        assert response.status_code == 401

    @override_settings(ROOT_URLCONF=__name__)
    def test_admin_or_read_only_post_allowed_admin(
        self, api_client, plain_admin
    ):
        """POST on admin-or-read-only view must be allowed for admin."""
        api_client.force_authenticate(user=plain_admin)
        response = api_client.post("/test/admin-or-read/", {}, format="json")
        assert response.status_code == 201

    @override_settings(ROOT_URLCONF=__name__)
    def test_customer_view_allows_verified_customer(
        self, api_client, plain_user
    ):
        """Customer view must return 200 for verified customer."""
        api_client.force_authenticate(user=plain_user)
        response = api_client.get("/test/customer/")
        assert response.status_code == 200

    @override_settings(ROOT_URLCONF=__name__)
    def test_customer_view_denies_unverified(
        self, api_client, plain_unverified_user
    ):
        """Customer view must return 403 for unverified user."""
        api_client.force_authenticate(user=plain_unverified_user)
        response = api_client.get("/test/customer/")
        assert response.status_code == 403

    @override_settings(ROOT_URLCONF=__name__)
    def test_verified_view_allows_verified_user(self, api_client, plain_user):
        """Verified view must return 200 for verified user."""
        api_client.force_authenticate(user=plain_user)
        response = api_client.get("/test/verified/")
        assert response.status_code == 200

    @override_settings(ROOT_URLCONF=__name__)
    def test_verified_view_denies_unverified_user(
        self, api_client, plain_unverified_user
    ):
        """Verified view must return 403 for unverified user."""
        api_client.force_authenticate(user=plain_unverified_user)
        response = api_client.get("/test/verified/")
        assert response.status_code == 403

    @override_settings(ROOT_URLCONF=__name__)
    def test_not_auth_view_allows_anonymous(self, api_client):
        """Not-authenticated view must return 200 for anonymous."""
        response = api_client.get("/test/not-auth/")
        assert response.status_code == 200

    @override_settings(ROOT_URLCONF=__name__)
    def test_not_auth_view_denies_authenticated(
        self, api_client, plain_user
    ):
        """Not-authenticated view must return 403 for authenticated user."""
        api_client.force_authenticate(user=plain_user)
        response = api_client.get("/test/not-auth/")
        assert response.status_code == 403

    @override_settings(ROOT_URLCONF=__name__)
    def test_error_response_shape_on_403(self, api_client, plain_user):
        """
        403 response must use standard error envelope.

        Permissions denied responses go through custom_exception_handler.
        Envelope must be consistent with all other error responses.
        """
        api_client.force_authenticate(user=plain_user)
        response = api_client.get("/test/admin/")

        assert response.status_code == 403
        assert "success" in response.data
        assert response.data["success"] is False
        assert "message" in response.data
        assert "errors" in response.data
        assert "meta" in response.data