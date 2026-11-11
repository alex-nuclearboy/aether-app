"""Lease and deliver verification email jobs using PostgreSQL."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from smtplib import SMTPException
from urllib.parse import urlsplit

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from accounts.emails import (
    build_verification_message,
    verification_path_for_user,
)
from accounts.models import User, VerificationEmailJob


logger = logging.getLogger("aether.email_worker")

MAX_DELIVERY_ATTEMPTS = 5
DELIVERY_LEASE = timedelta(minutes=5)
RETRY_DELAYS = (
    timedelta(seconds=30),
    timedelta(minutes=2),
    timedelta(minutes=10),
    timedelta(minutes=30),
)
MAX_CLAIM_SCAN = 20


class DeliveryOutcome(StrEnum):
    """Possible results of handling one claimed email job."""

    SENT = "sent"
    CANCELLED = "cancelled"
    RETRY = "retry"
    FAILED = "failed"


@dataclass(frozen=True)
class ClaimedVerificationJob:
    """Identify a claim without holding a database lock during SMTP."""

    pk: int
    user_id: int
    recipient_email: str
    attempts: int
    lease_expires_at: datetime


def validate_public_origin(origin: str) -> str:
    """Require an explicit trusted origin, not a request-derived host."""
    try:
        parsed = urlsplit(origin)
        port = parsed.port
    except ValueError as exc:
        raise ValueError("Public origin is not a valid URL.") from exc

    valid_location = (
        parsed.scheme in {"http", "https"}
        and bool(parsed.hostname)
        and bool(parsed.netloc)
    )
    has_credentials = (
        parsed.username is not None or parsed.password is not None
    )
    has_extra_parts = (
        parsed.path not in {"", "/"}
        or bool(parsed.query)
        or bool(parsed.fragment)
    )
    if (
        not valid_location
        or has_credentials
        or has_extra_parts
        or any(char.isspace() for char in origin)
        or port == 0
    ):
        raise ValueError("Public origin must be an HTTP(S) origin only.")

    if settings.ENVIRONMENT == "production" and parsed.scheme != "https":
        raise ValueError("Production email links require HTTPS.")

    return origin.rstrip("/")


def claim_due_email_job(job_model, make_claim):
    """Lease one due email job while holding a PostgreSQL row lock."""
    now = timezone.now()
    due = (
        Q(status=job_model.Status.PENDING, available_at__lte=now)
        | Q(
            status=job_model.Status.PROCESSING,
            lease_expires_at__lte=now,
        )
    )
    with transaction.atomic():
        jobs = (
            job_model.objects.select_for_update(skip_locked=True)
            .filter(due)
            .order_by("available_at", "pk")[:MAX_CLAIM_SCAN]
        )
        for job in jobs:
            if job.attempts >= MAX_DELIVERY_ATTEMPTS:
                job.status = job_model.Status.FAILED
                job.lease_expires_at = None
                job.last_error_code = "lease_expired"
                job.save(
                    update_fields=[
                        "status", "lease_expires_at", "last_error_code"
                    ]
                )
                continue
            job.attempts += 1
            job.status = job_model.Status.PROCESSING
            job.lease_expires_at = now + DELIVERY_LEASE
            job.save(
                update_fields=["attempts", "status", "lease_expires_at"]
            )
            return make_claim(job)
    return None


def claimed_email_user(claim, finish_claim, cancelled_status):
    """Get the job's user, cancelling an orphaned job if necessary."""
    try:
        return User.objects.get(pk=claim.user_id)
    except User.DoesNotExist:
        finish_claim(
            claim,
            status=cancelled_status,
            lease_expires_at=None,
            last_error_code="missing_user",
        )
        return None


def mark_email_job_sent(claim, finish_claim, sent_status):
    """Finalise delivery only if the original lease is still held."""
    return finish_claim(
        claim,
        status=sent_status,
        sent_at=timezone.now(),
        lease_expires_at=None,
        last_error_code="",
    )


def send_email_message(message):
    """Treat a backend refusing delivery as a transport failure."""
    if message.send() != 1:
        raise OSError("Email backend did not accept the message.")


def claim_verification_job() -> ClaimedVerificationJob | None:
    """Claim a verification job using the shared outbox lease rules."""
    return claim_due_email_job(
        VerificationEmailJob,
        lambda job: ClaimedVerificationJob(
            pk=job.pk,
            user_id=job.user_id,
            recipient_email=job.recipient_email,
            attempts=job.attempts,
            lease_expires_at=job.lease_expires_at,
        ),
    )


def _finish_claim(claim: ClaimedVerificationJob, **updates) -> bool:
    """Prevent a late worker from changing a newer worker's result."""
    updated = VerificationEmailJob.objects.filter(
        pk=claim.pk,
        status=VerificationEmailJob.Status.PROCESSING,
        lease_expires_at=claim.lease_expires_at,
    ).update(**updates)
    return bool(updated)


def _retry_or_fail(
    claim: ClaimedVerificationJob, *, error_code: str = "transport"
) -> DeliveryOutcome:
    """Apply bounded backoff to a failed delivery attempt."""
    if claim.attempts >= MAX_DELIVERY_ATTEMPTS:
        _finish_claim(
            claim,
            status=VerificationEmailJob.Status.FAILED,
            lease_expires_at=None,
            last_error_code=error_code,
        )
        return DeliveryOutcome.FAILED

    delay = RETRY_DELAYS[claim.attempts - 1]
    _finish_claim(
        claim,
        status=VerificationEmailJob.Status.PENDING,
        lease_expires_at=None,
        available_at=timezone.now() + delay,
        last_error_code=error_code,
    )
    return DeliveryOutcome.RETRY


def _send_claimed_verification_email(
    claim: ClaimedVerificationJob, user: User, public_origin: str
) -> DeliveryOutcome:
    """Prepare and deliver a claimed job, applying bounded retry rules."""
    # Unexpected template or token failures must not stop the queue.
    try:
        path = verification_path_for_user(user)
        message = build_verification_message(
            recipient=claim.recipient_email,
            verification_url=public_origin + path,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error(
            "verification_email.preparation_failed "
            "job_id=%s error_type=%s",
            claim.pk,
            type(exc).__name__,
        )
        return _retry_or_fail(claim, error_code="preparation")

    try:
        send_email_message(message)
    except (OSError, SMTPException):
        return _retry_or_fail(claim)
    # An unexpected backend error is also a bounded job failure.
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error(
            "verification_email.delivery_failed "
            "job_id=%s error_type=%s",
            claim.pk,
            type(exc).__name__,
        )
        return _retry_or_fail(claim, error_code="delivery")

    mark_email_job_sent(
        claim, _finish_claim, VerificationEmailJob.Status.SENT
    )
    return DeliveryOutcome.SENT


def deliver_next_verification_email(origin: str) -> DeliveryOutcome | None:
    """Deliver one due job without holding a PostgreSQL lock over SMTP."""
    public_origin = validate_public_origin(origin)
    claim = claim_verification_job()
    if claim is None:
        return None

    user = claimed_email_user(
        claim, _finish_claim, VerificationEmailJob.Status.CANCELLED
    )
    if user is None:
        return DeliveryOutcome.CANCELLED

    if not user.is_active:
        _finish_claim(
            claim,
            status=VerificationEmailJob.Status.CANCELLED,
            lease_expires_at=None,
            last_error_code="inactive_user",
        )
        return DeliveryOutcome.CANCELLED

    if (
        user.is_email_verified
        or user.email.casefold() != claim.recipient_email.casefold()
    ):
        _finish_claim(
            claim,
            status=VerificationEmailJob.Status.CANCELLED,
            lease_expires_at=None,
            last_error_code="outdated_recipient",
        )
        return DeliveryOutcome.CANCELLED

    return _send_claimed_verification_email(claim, user, public_origin)
