"""GET-only registration page tests prior to enabling public sign-ups."""

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import translation

from accounts.forms import AetherRegistrationForm


def test_anonymous_registration_page_displays_existing_form(client):
    """Expose the four supported fields without creating an account."""
    response = client.get(reverse("register"))

    assert response.status_code == 200
    assert response.template_name == ["accounts/register.html"]
    assert isinstance(response.context["form"], AetherRegistrationForm)

    content = response.content.decode()
    for field in ("username", "email", "password1", "password2"):
        assert f'name="{field}"' in content
    assert 'name="csrfmiddlewaretoken"' in content
    assert 'css/pages/register.css' in content
    assert 'class="register__panel"' in content
    assert 'href="' + reverse("login") + '"' in content
    assert "Registration is not available yet." in content
    assert 'type="submit" disabled' in content


def test_registration_page_uses_active_language(client):
    """Prepare new labels for translation without enabling a switcher."""
    with translation.override("pl"):
        response = client.get(reverse("register"))

    assert response.status_code == 200
    assert b'<html lang="pl">' in response.content


@pytest.mark.django_db
def test_signed_in_user_is_redirected_to_profile(client):
    """Do not show account creation to a signed-in user."""
    user = get_user_model().objects.create_user(
        username="registered-member",
        email="registered@example.com",
        password="Safe-Test-Passphrase-729!",
    )
    client.force_login(user)

    response = client.get(reverse("register"))

    assert response.status_code == 302
    assert response.url == reverse("profile")


@pytest.mark.django_db
def test_registration_post_is_disabled(client):
    """Reject account creation until delivery and rate limits are ready."""
    response = client.post(
        reverse("register"),
        {
            "username": "test-member",
            "email": "member@example.com",
            "password1": "Safer-Test-Passphrase-729!",
            "password2": "Safer-Test-Passphrase-729!",
        },
    )

    assert response.status_code == 405
    assert get_user_model().objects.count() == 0
