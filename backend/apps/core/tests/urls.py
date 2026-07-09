# ─── Test URL Configuration ───────────────────────────────────────────────────

# These URL patterns are ONLY loaded when tests set
# ROOT_URLCONF = "apps.core.tests.conftest" via @pytest.mark.urls
# or when we override settings in a test.
# They are completely invisible to production traffic.
from django.urls import path, include
from .conftest import PublicView,AdminOnlyView,AuthenticatedView,AdminOrReadOnlyView,CustomerOnlyView,VerifiedOnlyView,NotAuthenticatedView,RaiseUnhandledExceptionView,RaiseValidationErrorView,EchoRequestIDView
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