"""Public pre-verification email correction and privacy safeguards."""

from unittest.mock import patch

import pytest
from django.contrib.auth import check_password_with_timing_attack_mitigation
from django.core import mail
from django.db import IntegrityError
from django.test import Client, override_settings
from django.urls import reverse
from django.utils.functional import Promise

from accounts.email_outbox import (
    VerificationQueueStatus,
    queue_verification_email,
)
from accounts.email_worker import (
    DeliveryOutcome,
    claim_verification_job,
    deliver_next_verification_email,
)
from accounts.forms import AetherEmailCorrectionForm
from accounts.models import PublicRequestCounter, User, VerificationEmailJob
from accounts.public_recovery import correct_unverified_registration_email
from accounts.tokens import email_verification_token

pytestmark = pytest.mark.django_db
CORRECTION_URL = "registration_correct_email"
DONE_URL = "registration_correct_email_done"
PASSWORD = "Safe-Example-Passphrase-729!"


@pytest.fixture(name="pending_member")
def create_pending_member():
    """Create a never-verified, active public registration account."""
    return User.objects.create_user(
        username="pending-member",
        email="mistyped@example.com",
        password=PASSWORD,
        email_verification_required=True,
    )


def correction_data(**overrides):
    """Return a correction form submission without sensitive identifiers."""
    data = {
        "username": "pending-member",
        "password": PASSWORD,
        "new_email": "corrected@example.com",
    }
    data.update(overrides)
    return data


def _post(client, **overrides):
    """Submit a public correction form."""
    return client.post(reverse(CORRECTION_URL), correction_data(**overrides))


def test_public_page_is_available_with_registration_disabled(client):
    """Keep recovery independent of the disabled registration gate."""
    with override_settings(REGISTRATION_ENABLED=False):
        response = client.get(reverse(CORRECTION_URL))
    assert response.status_code == 200
    assert isinstance(response.context["form"], AetherEmailCorrectionForm)
    assert b'name="username"' in response.content
    assert b'name="password"' in response.content
    assert b'name="new_email"' in response.content
    assert b'name="csrfmiddlewaretoken"' in response.content
    assert b'css/pages/register.css' in response.content
    assert "no-store" in response["Cache-Control"]
    assert not PublicRequestCounter.objects.exists()


def test_success_changes_email_and_cancels_old_job(
    client, pending_member,
):
    """Change address, invalidate the old token and queue only the new one."""
    assert queue_verification_email(pending_member.pk) == (
        VerificationQueueStatus.QUEUED
    )
    old_token = email_verification_token.make_token(pending_member)
    old_job = VerificationEmailJob.objects.get(user=pending_member)

    with patch("accounts.emails.EmailMultiAlternatives.send") as smtp:
        response = _post(client, new_email="corrected@EXAMPLE.COM")
    assert response.status_code == 302
    assert response.url == reverse(DONE_URL)
    smtp.assert_not_called()
    assert not mail.outbox
    assert "_auth_user_id" not in client.session

    pending_member.refresh_from_db()
    assert pending_member.email == "corrected@example.com"
    assert pending_member.verified_email == ""
    assert pending_member.email_verification_required is True
    assert pending_member.email_verification_sent_at is not None
    assert not email_verification_token.check_token(pending_member, old_token)

    old_job.refresh_from_db()
    assert old_job.status == VerificationEmailJob.Status.CANCELLED
    assert old_job.last_error_code == "email_changed"
    assert old_job.lease_expires_at is None
    new_job = VerificationEmailJob.objects.exclude(pk=old_job.pk).get()
    assert new_job.status == VerificationEmailJob.Status.PENDING
    assert new_job.recipient_email == pending_member.email
    assert deliver_next_verification_email("http://testserver") == (
        DeliveryOutcome.SENT
    )
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [pending_member.email]


@pytest.mark.usefixtures("pending_member")
def test_successful_correction_keeps_neutral_result(client):
    """Do not reveal whether the supplied registration is eligible."""
    good = _post(client)
    unknown = _post(client, username="missing-member")
    wrong = _post(client, password="wrong-password")
    for response in (good, unknown, wrong):
        assert response.status_code == 302
        assert response.url == reverse(DONE_URL)
    done = client.get(reverse(DONE_URL))
    assert b"If the account is eligible" in done.content
    assert b"pending-member" not in done.content
    assert b"corrected@example.com" not in done.content


@pytest.mark.parametrize(
    "state", ["inactive", "verified", "previously_verified", "internal",
              "staff", "superuser"]
)
def test_ineligible_users_cannot_change_email(
    client, pending_member, state,
):
    """Only an active account never verified through public registration."""
    if state == "inactive":
        pending_member.is_active = False
    elif state == "verified":
        pending_member.verified_email = pending_member.email
    elif state == "previously_verified":
        pending_member.verified_email = "previous@example.com"
    elif state == "internal":
        pending_member.email_verification_required = False
    elif state == "staff":
        pending_member.is_staff = True
    else:
        pending_member.is_superuser = True
    pending_member.save()

    response = _post(client)
    assert response.url == reverse(DONE_URL)
    pending_member.refresh_from_db()
    assert pending_member.email == "mistyped@example.com"
    assert not VerificationEmailJob.objects.exists()


def test_wrong_password_does_not_change_user_or_jobs(
    client, pending_member,
):
    """Never use login authentication, which rejects unverified accounts."""
    assert queue_verification_email(pending_member.pk)
    response = _post(client, password="incorrect")
    assert response.url == reverse(DONE_URL)
    pending_member.refresh_from_db()
    assert pending_member.email == "mistyped@example.com"
    assert VerificationEmailJob.objects.get().status == (
        VerificationEmailJob.Status.PENDING
    )


def test_existing_recipient_collision_is_neutral(client, pending_member):
    """Roll back a duplicate-address failure without cancelling old work."""
    User.objects.create_user(
        username="other-member", email="taken@example.com",
        password=PASSWORD,
    )
    queue_verification_email(pending_member.pk)
    response = _post(client, new_email="TAKEN@example.com")
    assert response.url == reverse(DONE_URL)
    pending_member.refresh_from_db()
    assert pending_member.email == "mistyped@example.com"
    assert VerificationEmailJob.objects.get().status == (
        VerificationEmailJob.Status.PENDING
    )


def test_same_address_is_neutral_and_does_not_replace_job(
    client, pending_member,
):
    """Use the public resend endpoint for a current address instead."""
    queue_verification_email(pending_member.pk)
    response = _post(client, new_email="MISTYPED@example.com")
    assert response.url == reverse(DONE_URL)
    assert VerificationEmailJob.objects.count() == 1
    assert VerificationEmailJob.objects.get().status == (
        VerificationEmailJob.Status.PENDING
    )


def test_invalid_form_does_not_lookup_user(client):
    """Show only field validation errors and no account state."""
    with patch(
        "accounts.views.correct_unverified_registration_email"
    ) as correct:
        response = _post(client, new_email="not-an-email")
    assert response.status_code == 200
    assert b'id="id_new_email_error"' in response.content
    correct.assert_not_called()


def test_ip_limit_exhaustion_returns_retry_after(client):
    """Count invalid and unknown submissions against the IP limit."""
    url = reverse(CORRECTION_URL)
    for _ in range(10):
        response = client.post(url, {"username": "wrong"})
        assert response.status_code == 200
    response = client.post(url, {"username": "wrong"})
    assert response.status_code == 429
    assert int(response["Retry-After"]) > 0
    assert "no-store" in response["Cache-Control"]
    assert PublicRequestCounter.objects.count() == 1


def test_missing_client_ip_fails_closed(client):
    """Do not verify credentials without consuming an IP allowance."""
    with patch("accounts.views.get_client_ip", return_value=None):
        response = _post(client)
    assert response.status_code == 503
    assert "no-store" in response["Cache-Control"]
    assert not PublicRequestCounter.objects.exists()


def test_username_limit_is_neutral(client, pending_member):
    """Reject the sixth password attempt without revealing an account."""
    for _ in range(5):
        assert _post(client, password="bad-password").url == (
            reverse(DONE_URL)
        )
    response = _post(client)
    assert response.url == reverse(DONE_URL)
    pending_member.refresh_from_db()
    assert pending_member.email == "mistyped@example.com"
    assert not VerificationEmailJob.objects.exists()
    assert PublicRequestCounter.objects.count() == 2


def test_case_insensitive_username_shares_its_allowance(
    client, pending_member,
):
    """Prevent case changes from bypassing a username allowance."""
    for _ in range(5):
        _post(client, username="PENDING-MEMBER", password="incorrect")
    assert _post(client).url == reverse(DONE_URL)
    pending_member.refresh_from_db()
    assert pending_member.email == "mistyped@example.com"


def test_no_csrf_token_rejected():
    """Require CSRF on anonymous correction submissions."""
    browser = Client(enforce_csrf_checks=True)
    response = browser.post(reverse(CORRECTION_URL), correction_data())
    assert response.status_code == 403
    assert not PublicRequestCounter.objects.exists()


def test_rollback_preserves_original_email_and_outbox(
    client, pending_member,
):
    """Roll back the address and cancellations if enqueuing fails."""
    queue_verification_email(pending_member.pk)
    with patch(
        "accounts.public_recovery.queue_verification_email",
        side_effect=RuntimeError("outbox unavailable"),
    ), pytest.raises(RuntimeError, match="outbox unavailable"):
        _post(client)
    pending_member.refresh_from_db()
    assert pending_member.email == "mistyped@example.com"
    assert VerificationEmailJob.objects.count() == 1
    assert VerificationEmailJob.objects.get().status == (
        VerificationEmailJob.Status.PENDING
    )


def test_unexpected_queue_status_rolls_back_email_correction(
    pending_member,
):
    """Preserve the account and old job if no new job is queued."""
    assert queue_verification_email(pending_member.pk) == (
        VerificationQueueStatus.QUEUED
    )
    old_job = VerificationEmailJob.objects.get(user=pending_member)
    with patch(
        "accounts.public_recovery.queue_verification_email",
        return_value=VerificationQueueStatus.TOO_SOON,
    ), pytest.raises(RuntimeError, match="not queued"):
        correct_unverified_registration_email(
            pending_member.username, PASSWORD, "corrected@example.com"
        )
    pending_member.refresh_from_db()
    old_job.refresh_from_db()
    assert pending_member.email == "mistyped@example.com"
    assert old_job.status == VerificationEmailJob.Status.PENDING
    assert VerificationEmailJob.objects.count() == 1


def test_unrelated_integrity_error_is_propagated(pending_member):
    """Do not disguise unrelated database errors as email conflicts."""
    with patch.object(
        User, "save", side_effect=IntegrityError("unrelated constraint")
    ), pytest.raises(IntegrityError, match="unrelated constraint"):
        correct_unverified_registration_email(
            pending_member.username, PASSWORD, "corrected@example.com"
        )
    pending_member.refresh_from_db()
    assert pending_member.email == "mistyped@example.com"
    assert not VerificationEmailJob.objects.exists()


def test_processing_job_is_cancelled_after_email_change(
    client, pending_member,
):
    """A claimed old job must not later be marked delivered."""
    queue_verification_email(pending_member.pk)
    claim = claim_verification_job()
    assert claim is not None
    assert _post(client).url == reverse(DONE_URL)
    old_job = VerificationEmailJob.objects.get(pk=claim.pk)
    assert old_job.status == VerificationEmailJob.Status.CANCELLED
    assert old_job.lease_expires_at is None
    assert deliver_next_verification_email("http://testserver") == (
        DeliveryOutcome.SENT
    )
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == ["corrected@example.com"]


def test_unknown_account_uses_password_timing_mitigation(client):
    """Never skip password work just because the username is unknown."""
    target = (
        "accounts.public_recovery."
        "check_password_with_timing_attack_mitigation"
    )
    with patch(
        target, wraps=check_password_with_timing_attack_mitigation
    ) as check:
        response = _post(client, username="unknown-member")
    assert response.url == reverse(DONE_URL)
    assert check.call_count == 1
    assert check.call_args.args[0] is None


def test_form_labels_are_translation_ready():
    """Keep added form text compatible with future locale files."""
    form = AetherEmailCorrectionForm()
    assert all(
        isinstance(form[name].label, Promise)
        for name in ("username", "password", "new_email")
    )


@override_settings(
    CLIENT_IP_META_PRECEDENCE_ORDER=("HTTP_X_FORWARDED_FOR",),
)
def test_production_header_is_required_for_email_correction(client):
    """Never fall back to REMOTE_ADDR when proxy evidence is absent."""
    response = _post(client)
    assert response.status_code == 503
    assert not PublicRequestCounter.objects.exists()


@override_settings(
    CLIENT_IP_META_PRECEDENCE_ORDER=("HTTP_X_FORWARDED_FOR",),
)
def test_production_header_meters_email_correction(client):
    """Use Koyeb's rightmost forwarded address for public allowances."""
    response = client.post(
        reverse(CORRECTION_URL), correction_data(username="unknown-member"),
        HTTP_X_FORWARDED_FOR="192.0.2.17, 203.0.113.25",
    )
    assert response.url == reverse(DONE_URL)
    assert PublicRequestCounter.objects.count() == 2
