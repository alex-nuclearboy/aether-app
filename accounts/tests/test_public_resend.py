"""Public resend tests: enumeration resistance, throttles and delivery."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from accounts.email_worker import (
    DeliveryOutcome,
    deliver_next_verification_email,
)
from accounts.models import PublicRequestCounter, User, VerificationEmailJob

pytestmark = pytest.mark.django_db
RESEND_URL = "registration_resend_email"
DONE_URL = "registration_resend_done"


@pytest.fixture(name="unverified_member")
def create_unverified_member():
    """Create a public account which still requires confirmation."""
    return User.objects.create_user(
        username="pending-member",
        email="pending@example.com",
        password="Safe-Example-Passphrase-729!",
        email_verification_required=True,
    )


def test_public_form_renders_without_consuming_limits(client):
    """Expose an anonymous CSRF-protected email-only form."""
    response = client.get(reverse(RESEND_URL))
    assert response.status_code == 200
    assert b'name="email"' in response.content
    assert b'name="csrfmiddlewaretoken"' in response.content
    assert b'css/pages/register.css' in response.content
    assert response["Cache-Control"].find("no-store") != -1
    assert not PublicRequestCounter.objects.exists()


def test_invalid_email_shows_error_without_disclosing_accounts(client):
    """Reject malformed input without looking up user accounts."""
    response = client.post(reverse(RESEND_URL), {"email": "not-an-email"})
    assert response.status_code == 200
    assert b'id="id_email_error"' in response.content
    assert not VerificationEmailJob.objects.exists()


def test_known_unverified_address_is_queued_without_smtp(
    client, unverified_member
):
    """Keep SMTP out of HTTP while delivering a valid queued job."""
    with patch("accounts.emails.EmailMultiAlternatives.send") as smtp:
        response = client.post(
            reverse(RESEND_URL), {"email": "PENDING@EXAMPLE.COM"}
        )
    assert response.status_code == 302
    assert response.url == reverse(DONE_URL)
    assert not mail.outbox
    smtp.assert_not_called()
    job = VerificationEmailJob.objects.get(user=unverified_member)
    assert job.recipient_email == unverified_member.email
    assert job.status == VerificationEmailJob.Status.PENDING
    assert deliver_next_verification_email("http://testserver") == (
        DeliveryOutcome.SENT
    )
    assert len(mail.outbox) == 1


def test_unknown_and_existing_addresses_have_same_public_result(
    client, unverified_member
):
    """Return the same status, destination and page for either address."""
    known = client.post(
        reverse(RESEND_URL), {"email": unverified_member.email}
    )
    unknown = client.post(
        reverse(RESEND_URL), {"email": "missing@example.com"}
    )
    assert known.status_code == unknown.status_code == 302
    assert known.url == unknown.url == reverse(DONE_URL)
    done = client.get(reverse(DONE_URL))
    assert b"If an eligible unverified account" in done.content
    assert unverified_member.email.encode() not in done.content


@pytest.mark.parametrize("account_state", ["verified", "inactive", "internal"])
def test_ineligible_accounts_do_not_get_email(
    client, unverified_member, account_state
):
    """Avoid recovery emails for verified, inactive or internal users."""
    if account_state == "verified":
        unverified_member.verified_email = unverified_member.email
    elif account_state == "inactive":
        unverified_member.is_active = False
    else:
        unverified_member.email_verification_required = False
    unverified_member.save()

    response = client.post(
        reverse(RESEND_URL), {"email": unverified_member.email}
    )
    assert response.url == reverse(DONE_URL)
    assert not VerificationEmailJob.objects.exists()


def test_repeat_request_does_not_duplicate_pending_job(
    client, unverified_member
):
    """Deduplicate active jobs despite repeated public submissions."""
    for _ in range(2):
        response = client.post(
            reverse(RESEND_URL), {"email": unverified_member.email}
        )
        assert response.url == reverse(DONE_URL)
    assert VerificationEmailJob.objects.count() == 1


def test_resend_address_allowance_is_neutral_after_three(
    client, unverified_member
):
    """Use one response for allowed and address-throttled requests."""
    for _ in range(3):
        response = client.post(
            reverse(RESEND_URL), {"email": unverified_member.email}
        )
        assert response.url == reverse(DONE_URL)
        VerificationEmailJob.objects.filter(
            status=VerificationEmailJob.Status.PENDING
        ).update(status=VerificationEmailJob.Status.SENT)
        User.objects.filter(pk=unverified_member.pk).update(
            email_verification_sent_at=timezone.now() - timedelta(minutes=2)
        )

    throttled = client.post(
        reverse(RESEND_URL), {"email": unverified_member.email}
    )
    assert throttled.status_code == 302
    assert throttled.url == reverse(DONE_URL)
    assert VerificationEmailJob.objects.count() == 3
    assert not mail.outbox


def test_ip_limit_returns_retry_after_and_no_store(client):
    """Reject the eleventh POST even when all addresses are unknown."""
    url = reverse(RESEND_URL)
    for number in range(10):
        response = client.post(
            url, {"email": f"unknown{number}@example.com"}
        )
        assert response.url == reverse(DONE_URL)

    response = client.post(url, {"email": "last@example.com"})
    assert response.status_code == 429
    assert response["Retry-After"].isdigit()
    assert int(response["Retry-After"]) > 0
    assert "no-store" in {
        directive.strip()
        for directive in response["Cache-Control"].split(",")
    }
    assert not VerificationEmailJob.objects.exists()


def test_missing_ip_fails_closed_without_creating_counter(client):
    """Do not accept public recovery POST without a trusted client IP."""
    with patch("accounts.views.get_client_ip", return_value=None):
        response = client.post(
            reverse(RESEND_URL), {"email": "missing@example.com"}
        )
    assert response.status_code == 503
    assert "no-store" in {
        directive.strip()
        for directive in response["Cache-Control"].split(",")
    }
    assert not PublicRequestCounter.objects.exists()


def test_csrf_is_required_for_public_resend():
    """Refuse unauthenticated cross-site POSTs."""
    browser = Client(enforce_csrf_checks=True)
    response = browser.post(
        reverse(RESEND_URL), {"email": "missing@example.com"}
    )
    assert response.status_code == 403
    assert not PublicRequestCounter.objects.exists()


def test_address_changed_before_recovery_lookup_is_not_queued(
    client, unverified_member
):
    """Never redirect an old-address request to a new recipient."""
    old_address = unverified_member.email
    unverified_member.email = "new@example.com"
    unverified_member.save(update_fields=["email"])
    response = client.post(reverse(RESEND_URL), {"email": old_address})
    assert response.url == reverse(DONE_URL)
    assert not VerificationEmailJob.objects.exists()


@override_settings(REGISTRATION_ENABLED=False)
def test_recovery_link_is_available_when_registration_is_disabled(client):
    """Allow existing unverified accounts to recover independently."""
    response = client.get(reverse(RESEND_URL))
    assert response.status_code == 200
    assert b"Request another verification link" in response.content
