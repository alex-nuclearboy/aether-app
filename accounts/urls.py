"""URL configuration for application authentication and account profile."""

from django.urls import path

from accounts.views import (
    AetherLoginView,
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
    path("logout/", AetherLogoutView.as_view(), name="logout"),
    path("profile/", ProfileView.as_view(), name="profile"),
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
