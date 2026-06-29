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
)

app_name = "accounts"

urlpatterns = [
    # ─── Auth ─────────────────────────────────────────
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),

    # ─── Email Verification ───────────────────────────
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
    path("resend-verification/", ResendVerificationView.as_view(), name="resend-verification"),

    # ─── Password ─────────────────────────────────────
    path("password-reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"),
    path("change-password/", ChangePasswordView.as_view(), name="change-password"),

    # ─── Profile ──────────────────────────────────────
    path("profile/", ProfileView.as_view(), name="profile"),
    path("profile/avatar/", AvatarUploadView.as_view(), name="avatar-upload"),
]