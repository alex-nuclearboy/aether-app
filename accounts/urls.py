"""URL configuration for application authentication and account profile."""

from django.urls import path

from accounts.views import (
    AetherLoginView,
    AetherLogoutView,
    EmailVerificationConfirmView,
    EmailVerificationResultView,
    ProfileView,
    RequestEmailVerificationView,
)


urlpatterns = [
    path("login/", AetherLoginView.as_view(), name="login"),
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
