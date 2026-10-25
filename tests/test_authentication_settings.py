"""Tests for application authentication URL settings."""

from django.conf import settings
from django.urls import reverse


def test_application_authentication_redirect_settings():
    """Use named Aether routes rather than Django's default profile page."""
    assert settings.LOGIN_URL == "login"
    assert settings.LOGIN_REDIRECT_URL == "home"
    assert settings.LOGOUT_REDIRECT_URL == "home"
    assert reverse(settings.LOGIN_URL) == "/login/"
    assert reverse(settings.LOGIN_REDIRECT_URL) == "/"
