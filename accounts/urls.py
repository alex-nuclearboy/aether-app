"""URL configuration for application authentication and account profile."""

from django.urls import path

from accounts.views import (
    AetherLoginView,
    AetherPasswordChangeView,
    AetherPasswordResetRequestView,
    AetherPasswordResetDoneView,
    AetherPasswordResetConfirmView,
    AetherPasswordResetCompleteView,
    AetherEmailCorrectionView,
    AetherEmailCorrectionDoneView,
    AetherLogoutView,
    AetherRegistrationView,
    AetherResendVerificationView,
    AetherResendDoneView,
    RegistrationCheckEmailView,
    EmailVerificationConfirmView,
    EmailVerificationResultView,
    ProfileView,
    RequestEmailVerificationView,
)


urlpatterns = [
    path("login/", AetherLoginView.as_view(), name="login"),
    path("register/", AetherRegistrationView.as_view(), name="register"),
    path(
        "register/check-email/",
        RegistrationCheckEmailView.as_view(),
        name="registration_check_email",
    ),
    path(
        "register/resend/",
        AetherResendVerificationView.as_view(),
        name="registration_resend_email",
    ),
    path(
        "register/resend/done/",
        AetherResendDoneView.as_view(),
        name="registration_resend_done",
    ),
    path(
        "register/correct-email/",
        AetherEmailCorrectionView.as_view(),
        name="registration_correct_email",
    ),
    path(
        "register/correct-email/done/",
        AetherEmailCorrectionDoneView.as_view(),
        name="registration_correct_email_done",
    ),
    path(
        "password/reset/",
        AetherPasswordResetRequestView.as_view(),
        name="password_reset",
    ),
    path(
        "password/reset/done/",
        AetherPasswordResetDoneView.as_view(),
        name="password_reset_done",
    ),
    path(
        "password/reset/confirm/<uidb64>/<token>/",
        AetherPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    path(
        "password/reset/complete/",
        AetherPasswordResetCompleteView.as_view(),
        name="password_reset_complete",
    ),
    path("logout/", AetherLogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path(
        "profile/change-password/",
        AetherPasswordChangeView.as_view(),
        name="password_change",
    ),
    path(
        "profile/verify-email/",
        RequestEmailVerificationView.as_view(),
        name="email_verification_request",
    ),
    path(
        "email/verify/<uidb64>/<token>/",
        EmailVerificationConfirmView.as_view(),
        name="email_verification_confirm",
    ),
    path(
        "email/verification-result/",
        EmailVerificationResultView.as_view(),
        name="email_verification_result",
    ),
]
