"""Gated registration views and submission integration tests."""

import re
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import translation

from accounts.forms import AetherRegistrationForm
from accounts.models import User, VerificationEmailJob
from accounts.tests.registration_helpers import registration_data


@override_settings(REGISTRATION_ENABLED=False)
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
@override_settings(REGISTRATION_ENABLED=False)
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


@override_settings(REGISTRATION_ENABLED=True)
def test_enabled_registration_page_shows_submit_button(client):
    """Offer enabled submission only under an explicit test override."""
    response = client.get(reverse("register"))
    assert response.status_code == 200
    assert b'Registration is not available yet.' not in response.content
    assert b'type="submit" disabled' not in response.content


@pytest.mark.django_db
@override_settings(REGISTRATION_ENABLED=True)
def test_registration_creates_pending_account_and_queues_email(client):
    """Create one unverified account and outbox job without SMTP I/O."""
    response = client.post(reverse("register"), registration_data())

    assert response.status_code == 302
    assert response.url == reverse("registration_check_email")
    user = User.objects.get(username="test-member")
    assert user.email_verification_required is True
    assert user.is_email_verified is False
    assert user.is_active is True
    assert user.check_password("Safer-Test-Passphrase-729!")
    job = VerificationEmailJob.objects.get(user=user)
    assert job.status == VerificationEmailJob.Status.PENDING
    assert job.recipient_email == user.email
    assert not mail.outbox
    assert "_auth_user_id" not in client.session


@pytest.mark.django_db
@override_settings(REGISTRATION_ENABLED=True)
def test_invalid_registration_renders_field_errors_without_creating(client):
    """Show bound Django errors in the same form next to its fields."""
    response = client.post(
        reverse("register"),
        registration_data(password2="another-password"),
    )
    assert response.status_code == 200
    assert response.context["form"].errors.as_data()["password2"][0].code == (
        "password_mismatch"
    )
    assert b'id="id_password2_error"' in response.content
    assert User.objects.count() == 0
    assert len(mail.outbox) == 0


@pytest.mark.django_db
@override_settings(REGISTRATION_ENABLED=True)
def test_existing_email_is_reported_as_a_field_error(client):
    """Return the email duplicate error without delivering a message."""
    User.objects.create_user(
        username="other-member",
        email="MEMBER@example.com",
        password="Another-Test-Passphrase-123!",
    )
    response = client.post(reverse("register"), registration_data())
    assert response.status_code == 200
    assert response.context["form"].errors.as_data()["email"][0].code == (
        "unique"
    )
    assert User.objects.count() == 1
    assert len(mail.outbox) == 0


@pytest.mark.django_db
@override_settings(REGISTRATION_ENABLED=True)
def test_registration_race_attaches_conflict_to_username(client):
    """Expose known PostgreSQL races at the matching form input."""
    error = ValidationError(
        {"username": ValidationError("Already used.", code="unique")}
    )
    with patch(
        "accounts.views.create_registration_user",
        side_effect=error,
    ):
        response = client.post(reverse("register"), registration_data())
    assert response.status_code == 200
    assert response.context["form"].errors.as_data()["username"][0].code == (
        "unique"
    )
    assert b'id="id_username_error"' in response.content
    assert User.objects.count() == 0
    assert not mail.outbox


@pytest.mark.django_db
@override_settings(REGISTRATION_ENABLED=True)
def test_registration_does_not_call_synchronous_smtp(client):
    """Do not perform any email transport during registration POST."""
    with patch("accounts.emails.EmailMultiAlternatives.send") as smtp:
        response = client.post(reverse("register"), registration_data())

    assert response.status_code == 302
    assert response.url == reverse("registration_check_email")
    assert User.objects.filter(username="test-member").exists()
    assert VerificationEmailJob.objects.count() == 1
    smtp.assert_not_called()
    assert not mail.outbox


@pytest.mark.django_db
@override_settings(REGISTRATION_ENABLED=True)
def test_registration_rejects_post_without_csrf():
    """Deny anonymous account creation without a valid CSRF token."""
    browser = Client(enforce_csrf_checks=True)
    response = browser.post(reverse("register"), registration_data())
    assert response.status_code == 403
    assert not User.objects.exists()


@pytest.mark.django_db
@override_settings(REGISTRATION_ENABLED=True)
def test_registration_post_redirects_signed_in_user(client):
    """Prevent existing authenticated users from creating another account."""
    user = User.objects.create_user(
        username="signed-in-member",
        email="signed-in@example.com",
        password="Another-Test-Passphrase-123!",
    )
    client.force_login(user)
    response = client.post(reverse("register"), registration_data())
    assert response.status_code == 302
    assert response.url == reverse("profile")
    assert User.objects.count() == 1


def test_check_email_page_is_generic_and_translatable(client):
    """Do not expose the newly created address through the result URL."""
    with translation.override("pl"):
        response = client.get(reverse("registration_check_email"))
    assert response.status_code == 200
    assert b'<html lang="pl">' in response.content
    assert b'member@example.com' not in response.content
    assert b'css/pages/register.css' in response.content


@pytest.mark.django_db
@override_settings(REGISTRATION_ENABLED=True)
def test_registration_accepts_a_valid_csrf_origin():
    """Confirm that the browser can submit after receiving a CSRF token."""
    browser = Client(enforce_csrf_checks=True)
    page = browser.get(reverse("register"))
    assert page.status_code == 200
    match = re.search(
        rb'name="csrfmiddlewaretoken" value="([^"]+)"',
        page.content,
    )
    assert match is not None
    data = {
        **registration_data(),
        "csrfmiddlewaretoken": match.group(1).decode(),
    }
    response = browser.post(
        reverse("register"),
        data,
        HTTP_ORIGIN="http://testserver",
    )
    assert response.status_code == 302
    assert response.url == reverse("registration_check_email")
    assert User.objects.filter(username="test-member").exists()
    assert not mail.outbox
    assert VerificationEmailJob.objects.count() == 1
