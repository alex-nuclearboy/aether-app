"""Persistence and reservation tests for verification email jobs."""

from datetime import timedelta

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from accounts.email_outbox import (
    VerificationQueueStatus,
    queue_verification_email,
)
from accounts.models import User, VerificationEmailJob

pytestmark = pytest.mark.django_db


@pytest.fixture(name="member")
def make_member():
    """Provide one unverified account without delivery requirements."""
    return User.objects.create_user(
        username="outbox-member",
        email="member@example.com",
        password="ExamplePassphrase728!",
    )


def test_queues_one_job_without_sending_mail(member, mailoutbox):
    """Persist a snapshot of the address without generating a token."""
    assert queue_verification_email(member.pk) == (
        VerificationQueueStatus.QUEUED
    )
    job = VerificationEmailJob.objects.get(user=member)
    member.refresh_from_db()

    assert job.recipient_email == "member@example.com"
    assert job.status == VerificationEmailJob.Status.PENDING
    assert job.attempts == 0
    assert job.lease_expires_at is None
    assert job.sent_at is None
    assert member.email_verification_sent_at is not None
    assert mailoutbox == []


def test_repeated_request_does_not_create_another_active_job(member):
    """Re-use a pending request rather than creating duplicates."""
    assert queue_verification_email(member.pk) == (
        VerificationQueueStatus.QUEUED
    )
    assert queue_verification_email(member.pk) == (
        VerificationQueueStatus.ALREADY_QUEUED
    )
    assert VerificationEmailJob.objects.count() == 1


def test_verified_address_does_not_create_a_job(member):
    """Never enqueue a link for an already verified address."""
    member.verified_email = member.email
    member.save(update_fields=["verified_email"])

    assert queue_verification_email(member.pk) == (
        VerificationQueueStatus.VERIFIED
    )
    assert not VerificationEmailJob.objects.exists()


def test_cooldown_applies_without_an_active_job(member):
    """Retain the existing one-minute per-account request interval."""
    member.email_verification_sent_at = timezone.now()
    member.save(update_fields=["email_verification_sent_at"])

    assert queue_verification_email(member.pk) == (
        VerificationQueueStatus.TOO_SOON
    )
    assert not VerificationEmailJob.objects.exists()


def test_cooldown_allows_a_later_request(member):
    """Accept a new request when the previous reservation has expired."""
    member.email_verification_sent_at = timezone.now() - timedelta(minutes=2)
    member.save(update_fields=["email_verification_sent_at"])

    assert queue_verification_email(member.pk) == (
        VerificationQueueStatus.QUEUED
    )


def test_changed_email_receives_a_separate_job(member):
    """Keep the old recipient snapshot for stale-job checks by the worker."""
    queue_verification_email(member.pk)
    member.email = "corrected@example.com"
    member.email_verification_sent_at = None
    member.save(update_fields=["email", "email_verification_sent_at"])

    assert queue_verification_email(member.pk) == (
        VerificationQueueStatus.QUEUED
    )
    assert set(
        VerificationEmailJob.objects.values_list(
            "recipient_email", flat=True
        )
    ) == {"member@example.com", "corrected@example.com"}


def test_database_rejects_duplicate_active_jobs(member):
    """Enforce de-duplication in PostgreSQL, not only in Python."""
    queue_verification_email(member.pk)
    with pytest.raises(IntegrityError), transaction.atomic():
        VerificationEmailJob.objects.create(
            user=member, recipient_email=member.email
        )

    assert VerificationEmailJob.objects.count() == 1


def test_terminal_job_allows_a_later_request(member):
    """Keep delivery history while allowing another scheduled message."""
    queue_verification_email(member.pk)
    VerificationEmailJob.objects.update(
        status=VerificationEmailJob.Status.SENT,
        sent_at=timezone.now(),
    )
    User.objects.filter(pk=member.pk).update(
        email_verification_sent_at=timezone.now() - timedelta(minutes=2)
    )

    assert queue_verification_email(member.pk) == (
        VerificationQueueStatus.QUEUED
    )
    assert VerificationEmailJob.objects.count() == 2


def test_rollback_discards_job_and_cooldown_reservation(member):
    """Roll back both the queued job and the account reservation."""
    with pytest.raises(RuntimeError), transaction.atomic():
        assert queue_verification_email(member.pk) == (
            VerificationQueueStatus.QUEUED
        )
        raise RuntimeError("discard transaction")

    member.refresh_from_db()
    assert member.email_verification_sent_at is None
    assert not VerificationEmailJob.objects.exists()
