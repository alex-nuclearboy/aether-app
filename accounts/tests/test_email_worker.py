"""PostgreSQL worker delivery, retry, and stale-job tests."""

import re
from datetime import timedelta
from queue import Queue
from threading import Barrier, Thread
from smtplib import SMTPException
from unittest.mock import patch

import pytest
from django.core import mail
from django.db import close_old_connections, connections
from django.test import override_settings
from django.utils import timezone

from accounts.email_outbox import queue_verification_email
from accounts.email_worker import (
    MAX_DELIVERY_ATTEMPTS,
    DeliveryOutcome,
    _finish_claim,
    claim_verification_job,
    deliver_next_verification_email,
    validate_public_origin,
)
from accounts.models import User, VerificationEmailJob

pytestmark = pytest.mark.django_db
PUBLIC_ORIGIN = "https://aether.example.com"


@pytest.fixture(name="member")
def create_member():
    """Create an account whose email requires confirmation."""
    return User.objects.create_user(
        username="worker-member",
        email="member@example.com",
        password="ExamplePassphrase728!",
        email_verification_required=True,
    )


def test_worker_delivers_multipart_email_without_request(member):
    """Use the trusted public origin for the queued verification link."""
    queue_verification_email(member.pk)

    assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
        DeliveryOutcome.SENT
    )

    job = VerificationEmailJob.objects.get(user=member)
    assert job.status == VerificationEmailJob.Status.SENT
    assert job.attempts == 1
    assert job.sent_at is not None
    assert job.lease_expires_at is None
    assert len(mail.outbox) == 1
    message = mail.outbox[0]
    assert message.to == [member.email]
    match = re.search(
        r"https://aether\.example\.com/email/verify/[^/\s]+/[^/\s]+/",
        message.body,
    )
    assert match is not None
    assert match.group() in message.alternatives[0].content


def test_worker_does_not_send_to_old_address(member):
    """Discard jobs when the user's address has changed."""
    queue_verification_email(member.pk)
    member.email = "corrected@example.com"
    member.save(update_fields=["email"])

    assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
        DeliveryOutcome.CANCELLED
    )
    assert VerificationEmailJob.objects.get().status == (
        VerificationEmailJob.Status.CANCELLED
    )
    assert not mail.outbox


def test_worker_cancels_verified_address(member):
    """Skip pending delivery when the account is already verified."""
    queue_verification_email(member.pk)
    member.verified_email = member.email
    member.save(update_fields=["verified_email"])

    assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
        DeliveryOutcome.CANCELLED
    )
    assert not mail.outbox


def test_worker_cancels_job_for_inactive_account(member):
    """Skip SMTP when the account was deactivated after enqueuing."""
    queue_verification_email(member.pk)
    member.is_active = False
    member.save(update_fields=["is_active"])

    assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
        DeliveryOutcome.CANCELLED
    )

    job = VerificationEmailJob.objects.get(user=member)
    assert job.status == VerificationEmailJob.Status.CANCELLED
    assert job.last_error_code == "inactive_user"
    assert job.lease_expires_at is None
    assert job.attempts == 1
    assert not mail.outbox


def test_worker_cancels_retry_after_account_deactivation(member):
    """Do not deliver a retry if the account became inactive."""
    queue_verification_email(member.pk)
    with patch(
        "accounts.emails.EmailMultiAlternatives.send",
        side_effect=SMTPException("test transport interruption"),
    ):
        assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
            DeliveryOutcome.RETRY
        )

    member.is_active = False
    member.save(update_fields=["is_active"])
    VerificationEmailJob.objects.update(
        available_at=timezone.now() - timedelta(seconds=1)
    )

    assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
        DeliveryOutcome.CANCELLED
    )
    job = VerificationEmailJob.objects.get(user=member)
    assert job.status == VerificationEmailJob.Status.CANCELLED
    assert job.last_error_code == "inactive_user"
    assert job.lease_expires_at is None
    assert job.attempts == 2
    assert not mail.outbox


def test_worker_is_idle_without_due_jobs():
    """A polling worker has nothing to do on an empty queue."""
    assert deliver_next_verification_email(PUBLIC_ORIGIN) is None


def test_missing_account_cancels_claimed_job(member):
    """Do not attempt delivery when account lookup fails."""
    queue_verification_email(member.pk)
    with patch(
        "accounts.email_worker.User.objects.get",
        side_effect=User.DoesNotExist,
    ):
        assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
            DeliveryOutcome.CANCELLED
        )
    assert VerificationEmailJob.objects.get().last_error_code == (
        "missing_user"
    )


def test_unaccepted_message_is_retried(member):
    """Treat a zero-count mail backend response as a delivery failure."""
    queue_verification_email(member.pk)
    with patch(
        "accounts.emails.EmailMultiAlternatives.send", return_value=0
    ):
        assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
            DeliveryOutcome.RETRY
        )
    assert VerificationEmailJob.objects.get().attempts == 1


def test_transient_smtp_failure_schedules_delayed_retry(member):
    """Persist a delayed attempt rather than sending in a tight loop."""
    queue_verification_email(member.pk)
    with patch(
        "accounts.emails.EmailMultiAlternatives.send",
        side_effect=SMTPException("test transport interruption"),
    ):
        assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
            DeliveryOutcome.RETRY
        )

    job = VerificationEmailJob.objects.get()
    assert job.status == VerificationEmailJob.Status.PENDING
    assert job.attempts == 1
    assert job.last_error_code == "transport"
    assert job.lease_expires_at is None
    assert job.available_at > timezone.now()
    assert deliver_next_verification_email(PUBLIC_ORIGIN) is None
    assert not mail.outbox


def test_retry_eventually_marks_job_failed(member):
    """Stop retrying after the configured number of failed attempts."""
    queue_verification_email(member.pk)
    for attempt in range(1, MAX_DELIVERY_ATTEMPTS + 1):
        VerificationEmailJob.objects.update(
            available_at=timezone.now() - timedelta(seconds=1)
        )
        with patch(
            "accounts.emails.EmailMultiAlternatives.send",
            side_effect=OSError("test transport interruption"),
        ):
            outcome = deliver_next_verification_email(PUBLIC_ORIGIN)
        expected = (
            DeliveryOutcome.FAILED
            if attempt == MAX_DELIVERY_ATTEMPTS
            else DeliveryOutcome.RETRY
        )
        assert outcome == expected

    job = VerificationEmailJob.objects.get()
    assert job.status == VerificationEmailJob.Status.FAILED
    assert job.attempts == MAX_DELIVERY_ATTEMPTS
    assert deliver_next_verification_email(PUBLIC_ORIGIN) is None


@pytest.mark.parametrize(
    "failed_helper",
    ["verification_path_for_user", "build_verification_message"],
)
def test_unexpected_preparation_error_is_retried(member, failed_helper):
    """Catch token and template errors without storing sensitive details."""
    queue_verification_email(member.pk)
    with (
        patch(
            f"accounts.email_worker.{failed_helper}",
            side_effect=RuntimeError("sensitive verification URL"),
        ),
        patch("accounts.email_worker.logger.error") as log_error,
    ):
        assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
            DeliveryOutcome.RETRY
        )

    job = VerificationEmailJob.objects.get(user=member)
    assert job.status == VerificationEmailJob.Status.PENDING
    assert job.last_error_code == "preparation"
    assert job.attempts == 1
    assert job.lease_expires_at is None
    assert job.available_at > timezone.now()
    assert not mail.outbox
    log_error.assert_called_once()
    assert "sensitive verification URL" not in str(log_error.call_args)
    assert "RuntimeError" in str(log_error.call_args)


def test_unexpected_delivery_error_is_retried(member):
    """Handle an unexpected mail backend error with bounded retry."""
    queue_verification_email(member.pk)
    with (
        patch(
            "accounts.emails.EmailMultiAlternatives.send",
            side_effect=ValueError("sensitive verification URL"),
        ),
        patch("accounts.email_worker.logger.error") as log_error,
    ):
        assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
            DeliveryOutcome.RETRY
        )

    job = VerificationEmailJob.objects.get(user=member)
    assert job.status == VerificationEmailJob.Status.PENDING
    assert job.last_error_code == "delivery"
    assert job.attempts == 1
    assert job.lease_expires_at is None
    assert job.available_at > timezone.now()
    assert not mail.outbox
    log_error.assert_called_once()
    assert "sensitive verification URL" not in str(log_error.call_args)


def test_unexpected_preparation_errors_stop_after_attempt_limit(member):
    """Do not retry a persistent rendering fault indefinitely."""
    queue_verification_email(member.pk)
    with (
        patch(
            "accounts.email_worker.build_verification_message",
            side_effect=RuntimeError("test template failure"),
        ),
        patch("accounts.email_worker.logger.error"),
    ):
        for attempt in range(1, MAX_DELIVERY_ATTEMPTS + 1):
            VerificationEmailJob.objects.update(
                available_at=timezone.now() - timedelta(seconds=1)
            )
            outcome = deliver_next_verification_email(PUBLIC_ORIGIN)
            expected = (
                DeliveryOutcome.FAILED
                if attempt == MAX_DELIVERY_ATTEMPTS
                else DeliveryOutcome.RETRY
            )
            assert outcome == expected

    job = VerificationEmailJob.objects.get(user=member)
    assert job.status == VerificationEmailJob.Status.FAILED
    assert job.last_error_code == "preparation"
    assert job.attempts == MAX_DELIVERY_ATTEMPTS
    assert job.lease_expires_at is None
    assert not mail.outbox


def test_failed_preparation_does_not_block_other_jobs(member):
    """Continue with other due jobs after a preparation failure."""
    queue_verification_email(member.pk)
    other = User.objects.create_user(
        username="other-worker-member",
        email="other-worker@example.com",
        password="ExamplePassphrase728!",
        email_verification_required=True,
    )
    queue_verification_email(other.pk)

    with (
        patch(
            "accounts.email_worker.verification_path_for_user",
            side_effect=RuntimeError("test token generation failure"),
        ),
        patch("accounts.email_worker.logger.error"),
    ):
        assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
            DeliveryOutcome.RETRY
        )
    assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
        DeliveryOutcome.SENT
    )
    assert VerificationEmailJob.objects.get(user=other).status == (
        VerificationEmailJob.Status.SENT
    )
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to == [other.email]


def test_worker_does_not_swallow_keyboard_interrupt(member):
    """Allow process shutdown to interrupt message preparation."""
    queue_verification_email(member.pk)
    with patch(
        "accounts.email_worker.verification_path_for_user",
        side_effect=KeyboardInterrupt,
    ):
        with pytest.raises(KeyboardInterrupt):
            deliver_next_verification_email(PUBLIC_ORIGIN)
    assert VerificationEmailJob.objects.get().status == (
        VerificationEmailJob.Status.PROCESSING
    )


def test_worker_recovers_expired_processing_lease(member):
    """Reclaim work abandoned by a crashed worker after lease expiry."""
    queue_verification_email(member.pk)
    first_claim = claim_verification_job()
    assert first_claim is not None
    VerificationEmailJob.objects.update(
        lease_expires_at=timezone.now() - timedelta(seconds=1)
    )

    assert deliver_next_verification_email(PUBLIC_ORIGIN) == (
        DeliveryOutcome.SENT
    )
    job = VerificationEmailJob.objects.get()
    assert job.status == VerificationEmailJob.Status.SENT
    assert job.attempts == 2


def test_stale_worker_cannot_overwrite_reclaimed_lease(member):
    """A superseded worker must not mark a newer lease as complete."""
    queue_verification_email(member.pk)
    first_claim = claim_verification_job()
    assert first_claim is not None
    VerificationEmailJob.objects.update(
        lease_expires_at=timezone.now() - timedelta(seconds=1)
    )
    second_claim = claim_verification_job()
    assert second_claim is not None
    assert second_claim.lease_expires_at != first_claim.lease_expires_at

    assert not _finish_claim(
        first_claim, status=VerificationEmailJob.Status.SENT
    )
    assert VerificationEmailJob.objects.get().status == (
        VerificationEmailJob.Status.PROCESSING
    )


def test_expired_max_attempt_lease_is_terminal(member):
    """Do not retry an abandoned job beyond the attempt limit."""
    queue_verification_email(member.pk)
    VerificationEmailJob.objects.update(
        status=VerificationEmailJob.Status.PROCESSING,
        attempts=MAX_DELIVERY_ATTEMPTS,
        lease_expires_at=timezone.now() - timedelta(seconds=1),
    )

    assert claim_verification_job() is None
    job = VerificationEmailJob.objects.get()
    assert job.status == VerificationEmailJob.Status.FAILED
    assert job.last_error_code == "lease_expired"


@pytest.mark.parametrize(
    "origin",
    [
        "", "example.com", "javascript://example.com", "https://user@host",
        "https://host/secret", "https://host?token=1", "https://host/#f",
        "https://host:99999", "https://host\n.example.com",
    ],
)
def test_worker_rejects_invalid_public_origins(origin):
    """Never build token URLs using ambiguous or untrusted URL parts."""
    with pytest.raises(ValueError):
        validate_public_origin(origin)


@override_settings(ENVIRONMENT="production")
def test_production_worker_rejects_plain_http():
    """Never send production verification links over plain HTTP."""
    with pytest.raises(ValueError, match="HTTPS"):
        validate_public_origin("http://aether.example.com")


@override_settings(ENVIRONMENT="development")
def test_development_origin_can_use_local_http():
    """Allow the local development server to use its normal HTTP scheme."""
    assert validate_public_origin("http://127.0.0.1:8000/") == (
        "http://127.0.0.1:8000"
    )


@pytest.mark.django_db(transaction=True)
def test_two_workers_cannot_claim_the_same_pending_job():
    """Use separate PostgreSQL connections for competing workers."""
    user = User.objects.create_user(
        username="concurrent-worker",
        email="concurrent@example.com",
        password="ExamplePassphrase728!",
    )
    queue_verification_email(user.pk)
    barrier = Barrier(3)
    results = Queue()

    def attempt_claim():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            results.put(claim_verification_job())
        finally:
            connections.close_all()

    workers = [Thread(target=attempt_claim) for _ in range(2)]
    for worker in workers:
        worker.start()
    barrier.wait(timeout=10)
    for worker in workers:
        worker.join(timeout=10)
    assert not any(worker.is_alive() for worker in workers)

    claimed = [results.get_nowait() for _ in workers]
    assert sum(job is not None for job in claimed) == 1
    assert VerificationEmailJob.objects.get().attempts == 1
