"""End-to-end tests for read-only profiles and email verification."""

# Independent test fixtures intentionally use similar account setup.
# pylint: disable=duplicate-code

import re
from datetime import timedelta
from smtplib import SMTPException
from unittest.mock import patch

import pytest
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from accounts.models import User
from accounts.tokens import email_verification_token

pytestmark = pytest.mark.django_db


@pytest.fixture(name="member")
def create_member():
    """Create an ordinary account for the verification flow."""
    return User.objects.create_user(
        username="test-member",
        email="member@example.com",
        password="test-password",
    )


def verification_url(user):
    """Produce a link from the same token generator used by email."""
    return reverse(
        "email_verification_confirm",
        kwargs={
            "uidb64": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": email_verification_token.make_token(user),
        },
    )


def test_profile_requires_login(client):
    """Protect account details from anonymous visitors."""
    response = client.get(reverse("profile"))
    assert response.status_code == 302
    assert response["Location"].startswith("/login/?next=")


def test_profile_is_read_only_with_unverified_email(client, member):
    """Display saved email and status, without prematurely adding editing."""
    client.force_login(member)
    response = client.get(reverse("profile"))
    assert response.status_code == 200
    assert b"member@example.com" in response.content
    assert b"Not verified" in response.content
    assert b"Send verification email" in response.content
    assert b'action="/profile/verify-email/"' in response.content
    assert b"Change email" not in response.content
    assert b"css/pages/profile.css" in response.content
    assert b'href="/profile/"' in response.content


def test_verified_profile_has_no_request_form(client, member):
    """Hide the send action once the current address is verified."""
    member.verified_email = member.email
    member.save(update_fields=["verified_email"])
    client.force_login(member)
    response = client.get(reverse("profile"))
    assert b"Verified" in response.content
    assert b"Send verification email" not in response.content


def test_anonymous_cannot_request_email(client):
    """Require a logged-in account for the send action."""
    response = client.post(reverse("email_verification_request"))
    assert response.status_code == 302
    assert response["Location"].startswith("/login/?next=")


def test_send_is_post_only(client, member):
    """Reject GET requests to the delivery endpoint."""
    client.force_login(member)
    response = client.get(reverse("email_verification_request"))
    assert response.status_code == 405
    assert not mail.outbox


def test_request_sends_multipart_email_and_absolute_link(client, member):
    """Send both bodies to the current email using the configured mailer."""
    client.force_login(member)
    response = client.post(
        reverse("email_verification_request"),
        secure=True,
    )
    assert response.status_code == 302
    assert response["Location"] == reverse("profile")
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [member.email]
    assert message.subject == "Verify your Aether email address"
    assert message.alternatives[0].mimetype == "text/html"
    match = re.search(
        r"https://testserver/email/verify/[^/\s]+/[^/\s]+/",
        message.body,
    )
    assert match is not None
    assert match.group() in message.alternatives[0].content
    member.refresh_from_db()
    assert member.email_verification_sent_at is not None
    assert member.verified_email == ""


def test_recipient_cannot_be_overridden_by_post_data(client, member):
    """Reject recipient substitution in browser-controlled POST fields."""
    client.force_login(member)
    response = client.post(
        reverse("email_verification_request"),
        {"email": "attacker@example.com"},
    )
    assert response.status_code == 302
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [member.email]


def test_repeat_request_is_throttled(client, member):
    """Keep at most one email per account in the cooldown interval."""
    client.force_login(member)
    url = reverse("email_verification_request")
    assert client.post(url).status_code == 302
    assert client.post(url).status_code == 302
    assert len(mail.outbox) == 1
    response = client.get(reverse("profile"))
    assert b"Please wait before requesting another email." in response.content


def test_request_succeeds_after_cooldown(client, member):
    """Allow another delivery after the persisted cooldown expires."""
    client.force_login(member)
    url = reverse("email_verification_request")
    assert client.post(url).status_code == 302
    User.objects.filter(pk=member.pk).update(
        email_verification_sent_at=timezone.now() - timedelta(minutes=2),
    )
    assert client.post(url).status_code == 302
    assert len(mail.outbox) == 2


def test_send_for_verified_email_is_noop(client, member):
    """Never send a verification link for an already verified address."""
    member.verified_email = member.email
    member.save(update_fields=["verified_email"])
    client.force_login(member)
    response = client.post(reverse("email_verification_request"))
    assert response.status_code == 302
    assert not mail.outbox
    member.refresh_from_db()
    assert member.email_verification_sent_at is None


def test_delivery_failure_allows_retry(client, member):
    """Do not hold a send reservation after SMTP rejects a message."""
    client.force_login(member)
    url = reverse("email_verification_request")
    with patch(
        "accounts.emails.EmailMultiAlternatives.send",
        side_effect=SMTPException("temporary failure"),
    ):
        response = client.post(url)
    assert response.status_code == 302
    member.refresh_from_db()
    assert member.email_verification_sent_at is None
    assert client.post(url).status_code == 302
    assert len(mail.outbox) == 1


def test_send_requires_csrf(member):
    """Protect the send action against cross-site request forgery."""
    browser = Client(enforce_csrf_checks=True)
    browser.force_login(member)
    response = browser.post(reverse("email_verification_request"))
    assert response.status_code == 403
    assert not mail.outbox


def test_verification_get_does_not_update_database(client, member):
    """Link previews must not consume the verification token."""
    url = verification_url(member)
    response = client.get(url)
    assert response.status_code == 200
    assert b"Confirm email" in response.content
    assert b'name="csrfmiddlewaretoken"' in response.content
    assert response["Referrer-Policy"] == "origin"
    assert "no-store" in response["Cache-Control"]
    member.refresh_from_db()
    assert member.verified_email == ""


def test_anonymous_can_confirm_by_post(client, member):
    """Make the confirmation route reusable for future registration."""
    url = verification_url(member)
    response = client.post(url)
    assert response.status_code == 302
    assert response["Location"] == reverse("email_verification_result")
    assert response["Referrer-Policy"] == "origin"
    member.refresh_from_db()
    assert member.is_email_verified
    result = client.get(reverse("email_verification_result"))
    assert b"Your email has been verified." in result.content
    assert b"Sign in" in result.content
    assert b"test-member" not in result.content


def test_repeated_confirmation_fails(client, member):
    """Do not accept tokens after their first use."""
    url = verification_url(member)
    assert client.post(url).status_code == 302
    assert client.post(url).status_code == 302
    result = client.get(reverse("email_verification_result"))
    assert b"invalid or has expired" in result.content


def test_changed_address_rejects_old_confirmation(client, member):
    """A token cannot verify an address changed since generation."""
    url = verification_url(member)
    User.objects.filter(pk=member.pk).update(email="changed@example.com")
    assert client.post(url).status_code == 302
    member.refresh_from_db()
    assert member.verified_email == ""


def test_invalid_uid_and_token_are_neutral(client):
    """Avoid disclosing user data through malformed links."""
    url = reverse(
        "email_verification_confirm",
        kwargs={"uidb64": "invalid", "token": "invalid-token"},
    )
    response = client.get(url)
    assert response.status_code == 200
    assert b"invalid or has expired" in response.content
    assert client.post(url).status_code == 302


def test_confirmation_requires_csrf(member):
    """Reject non-CSRF-protected confirmation POSTs."""
    browser = Client(enforce_csrf_checks=True)
    url = verification_url(member)
    assert browser.post(url).status_code == 403
    member.refresh_from_db()
    assert member.verified_email == ""


def test_confirmation_accepts_valid_csrf_origin(member):
    """Allow confirmation with a valid CSRF token and same-site origin."""
    browser = Client(enforce_csrf_checks=True)
    url = verification_url(member)

    response = browser.get(url)

    assert response.status_code == 200
    assert response["Referrer-Policy"] == "origin"

    csrf_token = re.search(
        rb'name="csrfmiddlewaretoken" value="([^"]+)"',
        response.content,
    ).group(1).decode()

    response = browser.post(
        url,
        {"csrfmiddlewaretoken": csrf_token},
        HTTP_ORIGIN="http://testserver",
    )


def test_http_logs_redact_verification_tokens(client, member):
    """Keep secret tokens out of Aether's request correlation logs."""
    url = verification_url(member)
    with patch("infrastructure.request_id.http_logger.log") as log:
        client.get(url)
    assert log.call_count == 1
    arguments = log.call_args.args
    assert arguments[2] == "GET"
    assert arguments[3] == "/email/verify/<redacted>/"
    assert url not in str(arguments)


def test_email_backend_returns_zero_and_can_be_retried(client, member):
    """Treat a backend response of zero messages as delivery failure."""
    client.force_login(member)
    url = reverse("email_verification_request")
    with patch(
        "accounts.emails.EmailMultiAlternatives.send",
        return_value=0,
    ):
        assert client.post(url).status_code == 302
    member.refresh_from_db()
    assert member.email_verification_sent_at is None
    assert client.post(url).status_code == 302
    assert len(mail.outbox) == 1
