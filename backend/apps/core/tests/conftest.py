# backend/apps/core/tests/conftest.py
"""
Core app test fixtures and test infrastructure.

What belongs here:
    ✓ Fixtures only needed by core tests
    ✓ Test views used to test middleware/permissions/exceptions
    ✓ URL patterns for those test views
    ✗ Anything needed by accounts/products/cart (goes in global conftest)

Why we define test views here instead of in a separate file:
    These views ONLY exist to exercise core infrastructure.
    They are never imported by production code.
    Keeping them in conftest makes them available to all core tests
    automatically without any import.
"""
from __future__ import annotations

import pytest
from django.urls import path, include
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.api.views import BaseAPIView
from apps.core.permissions import (
    IsAdmin,
    IsAdminOrReadOnly,
    IsCustomer,
    IsNotAuthenticated,
    IsVerified,
)


# ─── Minimal Test Views ───────────────────────────────────────────────────────
# These views exist ONLY for testing core infrastructure.
# They are registered in a test-only URL conf below.
# Production urls.py never includes these.

class PublicView(BaseAPIView):
    """
    Open to everyone. Tests that unauthenticated requests work.
    Uses BaseAPIView so we test our actual response envelope.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return self.success_response(
            data={"message": "public"},
            message="Public endpoint reached",
        )


class AuthenticatedView(BaseAPIView):
    """Requires authentication. Tests IsAuthenticated behavior."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return self.success_response(
            data={"user": str(request.user)},
            message="Authenticated endpoint reached",
        )


class AdminOnlyView(BaseAPIView):
    """Requires ADMIN role. Tests IsAdmin permission."""
    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        return self.success_response(
            data={"role": str(request.user.role)},
            message="Admin endpoint reached",
        )


class AdminOrReadOnlyView(BaseAPIView):
    """Tests IsAdminOrReadOnly — read open, write admin-only."""
    permission_classes = [IsAdminOrReadOnly]

    def get(self, request):
        return self.success_response(
            data={"method": "GET"},
            message="Read access granted",
        )

    def post(self, request):
        return self.created_response(
            data={"method": "POST"},
            message="Write access granted",
        )


class CustomerOnlyView(BaseAPIView):
    """Requires CUSTOMER role + verified. Tests IsCustomer permission."""
    permission_classes = [IsAuthenticated, IsCustomer]

    def get(self, request):
        return self.success_response(
            data={"role": "customer"},
            message="Customer endpoint reached",
        )


class VerifiedOnlyView(BaseAPIView):
    """Requires is_verified=True. Tests IsVerified permission."""
    permission_classes = [IsAuthenticated, IsVerified]

    def get(self, request):
        return self.success_response(
            data={"verified": True},
            message="Verified endpoint reached",
        )


class NotAuthenticatedView(BaseAPIView):
    """Requires unauthenticated user. Tests IsNotAuthenticated permission."""
    permission_classes = [IsNotAuthenticated]

    def get(self, request):
        return self.success_response(
            data={"guest": True},
            message="Guest endpoint reached",
        )


class RaiseUnhandledExceptionView(BaseAPIView):
    """
    Deliberately raises an unhandled exception.
    Tests that custom_exception_handler catches it and returns
    a proper 500 envelope instead of crashing Django.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        raise RuntimeError("Deliberate unhandled exception for testing")


class RaiseValidationErrorView(BaseAPIView):
    """
    Raises a DRF ValidationError.
    Tests that custom_exception_handler formats field errors correctly.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        from rest_framework.exceptions import ValidationError
        raise ValidationError({"email": ["Enter a valid email address."]})


class EchoRequestIDView(BaseAPIView):
    """
    Returns request.id in response.
    Tests that RequestIDMiddleware injects ID and
    BaseAPIView.transform_payload() puts it in meta.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        return self.success_response(
            data={"request_id": getattr(request, "id", None)},
            message="Request ID echoed",
        )


# ─── Test URL Configuration ───────────────────────────────────────────────────

# These URL patterns are ONLY loaded when tests set
# ROOT_URLCONF = "apps.core.tests.conftest" via @pytest.mark.urls
# or when we override settings in a test.
# They are completely invisible to production traffic.

test_urlpatterns = [
    path("test/public/",           PublicView.as_view(),              name="test-public"),
    path("test/auth/",             AuthenticatedView.as_view(),       name="test-auth"),
    path("test/admin/",            AdminOnlyView.as_view(),           name="test-admin"),
    path("test/admin-or-read/",    AdminOrReadOnlyView.as_view(),     name="test-admin-or-read"),
    path("test/customer/",         CustomerOnlyView.as_view(),        name="test-customer"),
    path("test/verified/",         VerifiedOnlyView.as_view(),        name="test-verified"),
    path("test/not-auth/",         NotAuthenticatedView.as_view(),    name="test-not-auth"),
    path("test/unhandled-error/",  RaiseUnhandledExceptionView.as_view(), name="test-unhandled"),
    path("test/validation-error/", RaiseValidationErrorView.as_view(),    name="test-validation"),
    path("test/request-id/",       EchoRequestIDView.as_view(),           name="test-request-id"),
]


# ─── User Fixtures for Core Tests ─────────────────────────────────────────────

@pytest.fixture
def plain_user(db):
    """
    Basic verified customer user for core infrastructure tests.

    Why not import from accounts conftest:
        Core must not depend on accounts app fixtures.
        Core is the foundation — it cannot import from apps built on top of it.
        If accounts breaks, core tests must still run independently.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        email="coretest@example.com",
        full_name="Core Test User",
        password="X!9vQm2#rLpZ",
        is_verified=True,
    )


@pytest.fixture
def plain_admin(db):
    """
    Admin user for core infrastructure tests.
    Same reasoning as plain_user — core-owned, no accounts dependency.
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_superuser(
        email="coreadmin@example.com",
        full_name="Core Admin User",
        password="X!9vQm2#rLpZ",
    )


@pytest.fixture
def plain_unverified_user(db):
    """Unverified user for IsVerified and IsCustomer permission tests."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        email="unverified_core@example.com",
        full_name="Unverified Core User",
        password="X!9vQm2#rLpZ",
        is_verified=False,
    )


@pytest.fixture
def auth_client_user(plain_user, api_client):
    """
    api_client force-authenticated as plain_user.

    Why we don't call it auth_client:
        auth_client is reserved for accounts conftest.
        Naming collision would cause pytest fixture shadowing —
        tests importing both conftest files would get unpredictable results.
    """
    api_client.force_authenticate(user=plain_user)
    return api_client


@pytest.fixture
def auth_client_admin(plain_admin, api_client):
    """api_client force-authenticated as plain_admin."""
    api_client.force_authenticate(user=plain_admin)
    return api_client