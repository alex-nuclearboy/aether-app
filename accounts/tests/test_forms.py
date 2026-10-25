"""Tests for the application authentication form."""

from django.contrib.auth.forms import AuthenticationForm

from accounts.forms import AetherAuthenticationForm


def test_authentication_form_extends_django_form():
    """Retain Django's built-in authentication and validation behaviour."""
    form = AetherAuthenticationForm()

    assert isinstance(form, AuthenticationForm)
    assert form.fields["username"].label == "Username or email"
    assert form.fields["password"].label == "Password"


def test_authentication_form_uses_neutral_errors():
    """Avoid claiming identifier matching is case-sensitive."""
    form = AetherAuthenticationForm()

    assert "case-sensitive" not in str(
        form.error_messages["invalid_login"]
    )
    assert "username or email" in str(
        form.error_messages["invalid_login"]
    )
