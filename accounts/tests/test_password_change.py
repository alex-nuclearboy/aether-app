"""Browser-level tests for authenticated password changes."""

import pytest
from django.contrib.auth import SESSION_KEY
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import PasswordChangeView
from django.core import mail
from django.test import Client
from django.urls import resolve, reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.email_worker import DeliveryOutcome
from accounts.models import PasswordResetEmailJob, User
from accounts.password_reset import request_password_reset_email
from accounts.password_reset_worker import deliver_next_password_reset_email
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


def test_password_change_link_is_shown_in_profile(client, member):
    """Expose the password change action in authenticated navigation."""
    client.force_login(member)
    response = client.get(reverse("profile"))
    assert response.status_code == 200
    assert f'href="{reverse("password_change")}"'.encode() in response.content
    assert b"Change password" in response.content


def test_password_change_invalidates_another_session(client, member):
    """Keep the initiating session but invalidate a second old session."""
    other_browser = Client()
    client.force_login(member)
    other_browser.force_login(member)
    assert other_browser.get(reverse("profile")).status_code == 200

    response = client.post(reverse("password_change"), _valid_data())
    assert response.status_code == 302
    assert client.get(reverse("profile")).status_code == 200
    other_response = other_browser.get(reverse("profile"))
    assert other_response.status_code == 302
    assert other_response.url.startswith("/login/?next=")


def test_password_change_invalidates_existing_reset_token(client, member):
    """Invalidate a previously issued Django reset token through the view."""
    client.force_login(member)
    member.refresh_from_db()
    previous_token = default_token_generator.make_token(member)
    reset_url = reverse(
        "password_reset_confirm",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(member.pk)),
            "token": previous_token,
        },
    )
    changed = client.post(reverse("password_change"), _valid_data())
    assert changed.status_code == 302
    member.refresh_from_db()
    assert not default_token_generator.check_token(member, previous_token)
    invalid_link = client.get(reset_url)
    assert invalid_link.status_code == 200
    assert invalid_link.context["validlink"] is False


def test_password_change_cancels_old_reset_delivery(client, member):
    """Do not deliver a reset message queued before password change."""
    client.force_login(member)
    request_password_reset_email(member.email)
    job = PasswordResetEmailJob.objects.get(user=member)
    assert job.status == PasswordResetEmailJob.Status.PENDING

    changed = client.post(reverse("password_change"), _valid_data())
    assert changed.status_code == 302
    assert deliver_next_password_reset_email("http://testserver") == (
        DeliveryOutcome.CANCELLED
    )
    job.refresh_from_db()
    assert job.status == PasswordResetEmailJob.Status.CANCELLED
    assert job.last_error_code == "outdated_account"
    assert not mail.outbox
