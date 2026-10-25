"""URL configuration for application authentication."""

from django.urls import path

from accounts.views import AetherLoginView, AetherLogoutView


urlpatterns = [
    path("login/", AetherLoginView.as_view(), name="login"),
    path("logout/", AetherLogoutView.as_view(), name="logout"),
]
