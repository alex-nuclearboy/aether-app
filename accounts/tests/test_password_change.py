"""Browser-level tests for authenticated password changes."""

import pytest
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.views import PasswordChangeView
from django.test import Client
from django.urls import resolve, reverse

from accounts.models import User
from accounts.views import AetherPasswordChangeView


pytestmark = pytest.mark.django_db
OLD_PASSWORD = "Old-Example-Password-618!"
NEW_PASSWORD = "New-Example-Password-947!"


@pytest.fixture(name="member")
def create_member():
    """Create a verified account permitted to sign in."""
    return User.objects.create_user(
        username="password-change-member",
        email="password-change-member@example.test",
        password=OLD_PASSWORD,
        email_verification_required=True,
        verified_email="password-change-member@example.test",
    )


def _valid_data():
    """Return a valid password-change submission."""
    return {
        "old_password": OLD_PASSWORD,
        "new_password1": NEW_PASSWORD,
        "new_password2": NEW_PASSWORD,
    }


def test_password_change_url_has_dedicated_view():
    """Keep the account action separate from anonymous password reset."""
    url = reverse("password_change")
    assert url == "/profile/change-password/"
    assert resolve(url).func.view_class is AetherPasswordChangeView
    assert issubclass(AetherPasswordChangeView, PasswordChangeView)


def test_anonymous_users_must_sign_in(client):
    """Do not show or process the form without a session."""
    url = reverse("password_change")
    assert client.get(url).url.startswith("/login/?next=")
    assert client.post(url, _valid_data()).url.startswith(
        "/login/?next="
    )


def test_authenticated_page_uses_shared_form_and_csrf(client, member):
    """Display all three password fields without leaking values."""
    client.force_login(member)
    response = client.get(reverse("password_change"))
    assert response.status_code == 200
    assert b"Change password" in response.content
    assert b'css/pages/register.css' in response.content
    assert b'name="csrfmiddlewaretoken"' in response.content
    for field in ("old_password", "new_password1", "new_password2"):
        assert f'name="{field}"'.encode() in response.content
    assert "no-store" in response["Cache-Control"]


def test_valid_change_preserves_current_login(client, member):
    """Django updates the signed-in session after saving the new hash."""
    client.force_login(member)
    old_session_key = client.session.session_key
    response = client.post(reverse("password_change"), _valid_data())
    assert response.status_code == 302
    assert response.url == reverse("profile")
    member.refresh_from_db()
    assert member.check_password(NEW_PASSWORD)
    assert not member.check_password(OLD_PASSWORD)
    assert str(client.session[SESSION_KEY]) == str(member.pk)
    assert client.session.session_key != old_session_key
    profile = client.get(reverse("profile"))
    assert profile.status_code == 200
    assert b"Your password has been changed successfully." in (
        profile.content
    )


def test_wrong_old_password_is_rejected(client, member):
    """Require knowledge of the current password."""
    client.force_login(member)
    data = _valid_data()
    data["old_password"] = "Incorrect-Password-814!"
    response = client.post(reverse("password_change"), data)
    assert response.status_code == 200
    assert response.context["form"].errors.get("old_password")
    member.refresh_from_db()
    assert member.check_password(OLD_PASSWORD)


def test_mismatched_new_passwords_are_rejected(client, member):
    """Require new-password confirmation."""
    client.force_login(member)
    data = _valid_data()
    data["new_password2"] = "A-Different-Password-705!"
    response = client.post(reverse("password_change"), data)
    assert response.status_code == 200
    assert response.context["form"].errors.get("new_password2")
    member.refresh_from_db()
    assert member.check_password(OLD_PASSWORD)


def test_password_validator_rejects_short_password(client, member):
    """Reuse Django's configured password validators."""
    client.force_login(member)
    data = _valid_data()
    data["new_password1"] = data["new_password2"] = "short"
    response = client.post(reverse("password_change"), data)
    assert response.status_code == 200
    assert response.context["form"].errors.get("new_password2")
    member.refresh_from_db()
    assert member.check_password(OLD_PASSWORD)


def test_password_change_requires_csrf(member):
    """Reject an unsafe request without a CSRF token."""
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(member)
    response = browser.post(reverse("password_change"), _valid_data())
    assert response.status_code == 403
    member.refresh_from_db()
    assert member.check_password(OLD_PASSWORD)
