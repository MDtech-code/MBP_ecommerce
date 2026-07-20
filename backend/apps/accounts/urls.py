from django.urls import path
from .views import (
    RegisterView,
    VerifyEmailView,
    ResendVerificationView,
    LoginView,
    LogoutView,
    TokenRefreshView,
    PasswordResetRequestView,
    PasswordResetConfirmView,
    ProfileView,
    ChangePasswordView,
    AvatarUploadView,
    AddressListCreateView,
    AddressDetailView,
    AddressSetDefaultView,
    DeleteAccountView,
    EmailChangeConfirmView,EmailChangeRequestView,SocialAuthView,
    SendSecurityOTPView,VerifySecurityOTPView
)

app_name = "accounts"

urlpatterns = [
    # ─── Auth ─────────────────────────────────────────
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/social/", SocialAuthView.as_view(), name="social-auth"),
    # apps/accounts/urls.py — add new routes

    path("security/send-otp/",    SendSecurityOTPView.as_view(),   name="security-send-otp"),
    path("security/verify-otp/",  VerifySecurityOTPView.as_view(), name="security-verify-otp"),

    # ─── Email Verification ───────────────────────────
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),

    # ─── Password reset─────────────────────────────────────
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),

    # ─── Profile ──────────────────────────────────────
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/avatar/", AvatarUploadView.as_view(), name="avatar-upload"),

    # ─── Addresses ────────────────────────────────────────────
    path("addresses/",                    AddressListCreateView.as_view(), name="address-list-create"),
    path("addresses/<int:pk>/",           AddressDetailView.as_view(),     name="address-detail"),
    path("addresses/<int:pk>/set-default/", AddressSetDefaultView.as_view(), name="address-set-default"),

    # ─── Email Change ──────────────────────────────────────────────────────
    path("update-email/",           EmailChangeRequestView.as_view(),   name="update-email"),
    path("update-email/confirm/",   EmailChangeConfirmView.as_view(),   name="update-email-confirm"),
    # ─── delete account  ────────────────────────────────────────────
    path("me/delete/", DeleteAccountView.as_view(), name="delete-account"),


]