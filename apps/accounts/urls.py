from django.urls import path

from .views import (
    AddressDetailView,
    AddressListCreateView,
    ChangePasswordView,
    ForgotPasswordView,
    LoginView,
    MeView,
    RefreshTokenView,
    RegisterView,
    ResendEmailVerificationView,
    ResetPasswordView,
    VerifyEmailView,
    VerifyPasswordResetCodeView,
)


urlpatterns = [
    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------
    path(
        "register/",
        RegisterView.as_view(),
        name="account-register",
    ),
    path(
        "login/",
        LoginView.as_view(),
        name="account-login",
    ),
    path(
        "refresh/",
        RefreshTokenView.as_view(),
        name="account-token-refresh",
    ),
    # -------------------------------------------------------------------------
    # Email verification
    # -------------------------------------------------------------------------
    path(
        "email/verify/",
        VerifyEmailView.as_view(),
        name="account-email-verify",
    ),
    path(
        "email/resend/",
        ResendEmailVerificationView.as_view(),
        name="account-email-resend",
    ),
    # -------------------------------------------------------------------------
    # Password recovery
    # -------------------------------------------------------------------------
    path(
        "password/forgot/",
        ForgotPasswordView.as_view(),
        name="account-password-forgot",
    ),
    path(
        "password/verify/",
        VerifyPasswordResetCodeView.as_view(),
        name="account-password-verify",
    ),
    path(
        "password/reset/",
        ResetPasswordView.as_view(),
        name="account-password-reset",
    ),
    # -------------------------------------------------------------------------
    # Authenticated account security
    # -------------------------------------------------------------------------
    path(
        "password/change/",
        ChangePasswordView.as_view(),
        name="account-password-change",
    ),
    # -------------------------------------------------------------------------
    # Current user
    # -------------------------------------------------------------------------
    path(
        "me/",
        MeView.as_view(),
        name="account-me",
    ),
    # -------------------------------------------------------------------------
    # Addresses
    # -------------------------------------------------------------------------
    path(
        "addresses/",
        AddressListCreateView.as_view(),
        name="address-list-create",
    ),
    path(
        "addresses/<uuid:pk>/",
        AddressDetailView.as_view(),
        name="address-detail",
    ),
]
