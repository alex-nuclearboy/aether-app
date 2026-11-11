"""End-to-end password reset requests and token confirmation."""

import re
from urllib.parse import urlsplit
from unittest.mock import patch

import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client, override_settings
from django.urls import reverse
from django.utils.functional import Promise

from accounts.forms import AetherPasswordResetRequestForm
from accounts.models import PasswordResetEmailJob, PublicRequestCounter, User
from accounts.password_reset_worker import (
    DeliveryOutcome,
    deliver_next_password_reset_email,
)


pytestmark = pytest.mark.django_db
PASSWORD = "Example-Strong-Passphrase-719!"
NEW_PASSWORD = "Different-Strong-Passphrase-826!"
ORIGIN = "http://testserver"


@pytest.fixture(name="verified_member")
def create_verified_member():
    """Create an active account with ownership of its email confirmed."""
    return User.objects.create_user(
        username="password-reset-member",
        email="reset-member@example.test",
        password=PASSWORD,
        email_verification_required=True,
        verified_email="reset-member@example.test",
    )


def _request(client, email="reset-member@example.test"):
    """Post a reset request through the public endpoint."""
    return client.post(reverse("password_reset"), {"email": email})


def test_reset_request_is_public_with_registration_disabled(client):
    """Password recovery remains available when registration is gated."""
    with override_settings(REGISTRATION_ENABLED=False):
        response = client.get(reverse("password_reset"))
    assert response.status_code == 200
    assert b'name="email"' in response.content
    assert b'name="csrfmiddlewaretoken"' in response.content
    assert "no-store" in response["Cache-Control"]
    assert not PublicRequestCounter.objects.exists()


def test_reset_is_queued_without_smtp(client, verified_member):
    """Only the independent worker may contact an email backend."""
    with patch("accounts.emails.EmailMultiAlternatives.send") as smtp:
        response = _request(client)
    assert response.status_code == 302
    assert response.url == reverse("password_reset_done")
    smtp.assert_not_called()
    assert not mail.outbox
    job = PasswordResetEmailJob.objects.get(user=verified_member)
    assert job.status == PasswordResetEmailJob.Status.PENDING
    assert job.attempts == 0
    assert job.account_signature
    assert "_auth_user_id" not in client.session


def test_unknown_and_ineligible_accounts_are_neutral(client):
    """Unknown, inactive and unverified accounts all see the same result."""
    for username, active, verified in (
        ("reset-disabled", False, True),
        ("reset-unverified", True, False),
    ):
        User.objects.create_user(
            username=username,
            email=f"{username}@example.test",
            password=PASSWORD,
            is_active=active,
            email_verification_required=True,
            verified_email=(f"{username}@example.test" if verified else ""),
        )
    for address in (
        "unknown@example.test",
        "reset-disabled@example.test",
        "reset-unverified@example.test",
    ):
        response = _request(client, email=address)
        assert response.status_code == 302
        assert response.url == reverse("password_reset_done")
    assert not PasswordResetEmailJob.objects.exists()


def test_reset_worker_sends_multipart_message(client, verified_member):
    """Keep the link out of the database and emit it through the worker."""
    _request(client)
    assert deliver_next_password_reset_email(ORIGIN) == DeliveryOutcome.SENT
    job = PasswordResetEmailJob.objects.get(user=verified_member)
    assert job.status == PasswordResetEmailJob.Status.SENT
    assert job.attempts == 1
    assert job.sent_at is not None
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [verified_member.email]
    match = re.search(
        r"http://testserver/password/reset/confirm/[^/\s]+/[^/\s]+/",
        message.body,
    )
    assert match is not None
    assert match.group() in message.alternatives[0].content


def test_password_reset_confirm_requires_valid_token(client, verified_member):
    """Django swaps a genuine token for a session-only form URL."""
    _request(client)
    deliver_next_password_reset_email(ORIGIN)
    link = re.search(
        r"http://testserver/password/reset/confirm/[^/\s]+/[^/\s]+/",
        mail.outbox[0].body,
    )
    assert link is not None
    old_token = default_token_generator.make_token(verified_member)
    response = client.get(urlsplit(link.group()).path)
    assert response.status_code == 302
    assert "set-password" in response["Location"]
    assert old_token not in response["Location"]
    assert response["Referrer-Policy"] == "origin"
    confirm = client.get(response["Location"])
    assert confirm.status_code == 200
    assert confirm.context["validlink"] is True
    assert verified_member.check_password(PASSWORD)
    response = client.post(
        response["Location"],
        {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
    )
    assert response.status_code == 302
    assert response.url == reverse("password_reset_complete")
    verified_member.refresh_from_db()
    assert verified_member.check_password(NEW_PASSWORD)
    assert not default_token_generator.check_token(verified_member, old_token)
    assert "_auth_user_id" not in client.session


def test_old_password_reset_url_does_not_work_after_change(
    client, verified_member,
):
    """Reject an earlier token when the stored password has changed."""
    _request(client)
    deliver_next_password_reset_email(ORIGIN)
    old_link = re.search(
        r"http://testserver/password/reset/confirm/[^/\s]+/[^/\s]+/",
        mail.outbox[0].body,
    )
    assert old_link is not None
    verified_member.set_password(NEW_PASSWORD)
    verified_member.save(update_fields=["password"])
    response = client.get(urlsplit(old_link.group()).path)
    assert response.status_code == 200
    assert response.context["validlink"] is False


def test_job_cancelled_after_password_change(client, verified_member):
    """Do not emit a late email after the requester's password changed."""
    _request(client)
    verified_member.set_password(NEW_PASSWORD)
    verified_member.save(update_fields=["password"])
    assert deliver_next_password_reset_email(ORIGIN) == (
        DeliveryOutcome.CANCELLED
    )
    assert PasswordResetEmailJob.objects.get().last_error_code == (
        "outdated_account"
    )
    assert not mail.outbox


def test_job_cancelled_after_deactivation(client, verified_member):
    """Deactivate a queued recipient without contacting SMTP."""
    _request(client)
    verified_member.is_active = False
    verified_member.save(update_fields=["is_active"])
    assert deliver_next_password_reset_email(ORIGIN) == (
        DeliveryOutcome.CANCELLED
    )
    assert not mail.outbox


def test_duplicate_request_does_not_create_two_jobs(client, verified_member):
    """Retain one active reset job despite repeated requests."""
    _request(client)
    _request(client)
    assert (
        PasswordResetEmailJob.objects.filter(user=verified_member).count()
        == 1
    )


def test_recent_sent_job_blocks_a_second_reset_request(
    client, verified_member,
):
    """Enforce the cooldown after the first job has been delivered."""
    assert _request(client).status_code == 302
    assert deliver_next_password_reset_email(ORIGIN) == (
        DeliveryOutcome.SENT
    )
    assert _request(client).status_code == 302
    jobs = PasswordResetEmailJob.objects.filter(user=verified_member)
    assert jobs.count() == 1
    assert jobs.get().status == PasswordResetEmailJob.Status.SENT
    assert len(mail.outbox) == 1


def test_ip_limit_fails_closed_and_has_retry_after(client):
    """Return HTTP 429 for exhausted anonymous IP allowances."""
    for _ in range(10):
        response = _request(client, email="unknown@example.test")
        assert response.status_code == 302
    response = _request(client, email="unknown@example.test")
    assert response.status_code == 429
    assert int(response["Retry-After"]) > 0
    assert "no-store" in response["Cache-Control"]


@override_settings(
    CLIENT_IP_META_PRECEDENCE_ORDER=("HTTP_X_FORWARDED_FOR",),
)
def test_missing_forwarded_ip_fails_closed(client):
    """Require trusted IP information before touching the database."""
    response = _request(client)
    assert response.status_code == 503
    assert not PublicRequestCounter.objects.exists()


def test_invalid_email_does_not_enqueue(client):
    """Keep validation on the public request form."""
    response = _request(client, email="not-an-email")
    assert response.status_code == 200
    assert not PasswordResetEmailJob.objects.exists()


def test_password_reset_form_label_is_lazy():
    """Retain Django translation objects without dynamic model access."""
    form = AetherPasswordResetRequestForm()
    assert isinstance(form["email"].label, Promise)


def test_reset_confirmation_is_csrf_protected(client, verified_member):
    """Require a CSRF token when changing credentials."""
    _request(client)
    deliver_next_password_reset_email(ORIGIN)
    url = re.search(
        r"http://testserver/password/reset/confirm/[^/\s]+/[^/\s]+/",
        mail.outbox[0].body,
    )
    assert url is not None
    strict = Client(enforce_csrf_checks=True)
    response = strict.get(urlsplit(url.group()).path)
    assert response.status_code == 302
    response = strict.post(
        response["Location"],
        {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD},
    )
    assert response.status_code == 403
    verified_member.refresh_from_db()
    assert verified_member.check_password(PASSWORD)
