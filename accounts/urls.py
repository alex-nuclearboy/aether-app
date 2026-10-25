"""URL configuration for application authentication."""

from django.contrib.auth.views import LogoutView
from django.urls import path

from accounts.views import AetherLoginView


urlpatterns = [
    path("login/", AetherLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
]
