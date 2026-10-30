"""Check that Aether's authentication responses use translation hooks."""

from unittest.mock import patch

import pytest
from django.urls import reverse
from django.utils.functional import Promise

from accounts.forms import AetherAuthenticationForm
from accounts.lockout_responses import lockout_response
from accounts.models import User
from accounts.validators import username_validator


def test_authentication_form_errors_remain_lazy():
    """Allow Django to resolve authentication errors in the active language."""
    form = AetherAuthenticationForm()

    assert isinstance(form.error_messages["invalid_login"], Promise)
    assert isinstance(form.error_messages["inactive"], Promise)
    assert isinstance(form.fields["username"].label, Promise)


def test_model_validation_text_remains_lazy():
    """Retain translation hooks for account validation and field labels."""
    assert isinstance(User._meta.get_field("username").verbose_name, Promise)
    assert isinstance(User._meta.get_field("email").verbose_name, Promise)
    assert isinstance(username_validator.message, Promise)


@pytest.mark.django_db
def test_login_and_logout_feedback_are_translated(client):
    """Resolve success messages through gettext when requests are handled."""
    member = User.objects.create_user(
        username="translation.member",
        email="translation.member@example.test",
        password="valid-test-password",
    )

    with patch(
        "accounts.views._",
        side_effect=lambda message: f"translated: {message}",
    ) as translate:
        login = client.post(
            reverse("login"),
            {"username": member.username, "password": "valid-test-password"},
        )
        logout = client.post(reverse("logout"))

    assert login.status_code == 302
    assert logout.status_code == 302
    assert translate.call_count == 2
    content = client.get(reverse("home")).content.decode()
    assert "translated: You have signed in successfully." in content
    assert "translated: You have signed out successfully." in content


def test_lockout_response_is_translated(rf):
    """Translate the visible HTTP 429 response without changing its status."""
    request = rf.get("/login/")
    with (
        patch(
            "accounts.lockout_responses.get_lockout_remaining_seconds",
            return_value=0,
        ),
        patch(
            "accounts.lockout_responses._",
            side_effect=lambda message: f"translated: {message}",
        ) as translate,
    ):
        response = lockout_response(
            request,
            None,
            {"username": "unknown-member"},
        )

    assert response.status_code == 429
    assert response.content.decode() == (
        "translated: Too many failed login attempts. "
        "Please try again later."
    )
    translate.assert_called_once()
