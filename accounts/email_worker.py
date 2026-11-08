"""Lease and deliver verification email jobs using PostgreSQL."""

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


def claim_verification_job() -> ClaimedVerificationJob | None:
    """Atomically claim a due or expired-lease job in PostgreSQL."""
    now = timezone.now()
    due = (
        Q(status=VerificationEmailJob.Status.PENDING, available_at__lte=now)
        | Q(
            status=VerificationEmailJob.Status.PROCESSING,
            lease_expires_at__lte=now,
        )
    )
    with transaction.atomic():
        jobs = (
            VerificationEmailJob.objects.select_for_update(skip_locked=True)
            .filter(due)
            .order_by("available_at", "pk")[:MAX_CLAIM_SCAN]
        )
        for job in jobs:
            if job.attempts >= MAX_DELIVERY_ATTEMPTS:
                job.status = VerificationEmailJob.Status.FAILED
                job.lease_expires_at = None
                job.last_error_code = "lease_expired"
                job.save(
                    update_fields=[
                        "status", "lease_expires_at", "last_error_code"
                    ]
                )
                continue

            job.attempts += 1
            job.status = VerificationEmailJob.Status.PROCESSING
            job.lease_expires_at = now + DELIVERY_LEASE
            job.save(
                update_fields=["attempts", "status", "lease_expires_at"]
            )
            return ClaimedVerificationJob(
                pk=job.pk,
                user_id=job.user_id,
                recipient_email=job.recipient_email,
                attempts=job.attempts,
                lease_expires_at=job.lease_expires_at,
            )

    return None


def _finish_claim(claim: ClaimedVerificationJob, **updates) -> bool:
    """Prevent a late worker from changing a newer worker's result."""
    updated = VerificationEmailJob.objects.filter(
        pk=claim.pk,
        status=VerificationEmailJob.Status.PROCESSING,
        lease_expires_at=claim.lease_expires_at,
    ).update(**updates)
    return bool(updated)


def _retry_or_fail(claim: ClaimedVerificationJob) -> DeliveryOutcome:
    """Back off transient SMTP errors, then stop after five attempts."""
    if claim.attempts >= MAX_DELIVERY_ATTEMPTS:
        _finish_claim(
            claim,
            status=VerificationEmailJob.Status.FAILED,
            lease_expires_at=None,
            last_error_code="transport",
        )
        return DeliveryOutcome.FAILED

    delay = RETRY_DELAYS[claim.attempts - 1]
    _finish_claim(
        claim,
        status=VerificationEmailJob.Status.PENDING,
        lease_expires_at=None,
        available_at=timezone.now() + delay,
        last_error_code="transport",
    )
    return DeliveryOutcome.RETRY


def deliver_next_verification_email(origin: str) -> DeliveryOutcome | None:
    """Deliver one due job without holding a PostgreSQL lock over SMTP."""
    public_origin = validate_public_origin(origin)
    claim = claim_verification_job()
    if claim is None:
        return None

    try:
        user = User.objects.get(pk=claim.user_id)
    except User.DoesNotExist:
        _finish_claim(
            claim,
            status=VerificationEmailJob.Status.CANCELLED,
            lease_expires_at=None,
            last_error_code="missing_user",
        )
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

    path = verification_path_for_user(user)
    message = build_verification_message(
        recipient=claim.recipient_email,
        verification_url=public_origin + path,
    )

    try:
        if message.send() != 1:
            raise OSError("Email backend did not accept the message.")
    except (OSError, SMTPException):
        return _retry_or_fail(claim)

    _finish_claim(
        claim,
        status=VerificationEmailJob.Status.SENT,
        sent_at=timezone.now(),
        lease_expires_at=None,
        last_error_code="",
    )
    return DeliveryOutcome.SENT
