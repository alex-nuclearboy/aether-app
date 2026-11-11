"""Claim and deliver password reset emails outside HTTP requests."""

import logging
from dataclasses import dataclass
from datetime import datetime
from smtplib import SMTPException

from django.utils import timezone
from django.utils.crypto import constant_time_compare

from accounts.email_worker import (
    MAX_DELIVERY_ATTEMPTS,
    RETRY_DELAYS,
    DeliveryOutcome,
    claim_due_email_job,
    claimed_email_user,
    mark_email_job_sent,
    send_email_message,
    validate_public_origin,
)
from accounts.emails import (
    build_password_reset_message,
    password_reset_path_for_user,
)
from accounts.models import PasswordResetEmailJob, User
from accounts.password_reset import (
    account_state_signature,
    password_reset_eligible,
)


logger = logging.getLogger("aether.email_worker")


@dataclass(frozen=True)
class ClaimedResetJob:
    """Identify a leased row without holding the lock during delivery."""

    pk: int
    user_id: int
    recipient_email: str
    account_signature: str
    attempts: int
    lease_expires_at: datetime


def claim_password_reset_job() -> ClaimedResetJob | None:
    """Claim a password-reset job with the shared PostgreSQL lease rules."""
    return claim_due_email_job(
        PasswordResetEmailJob,
        lambda job: ClaimedResetJob(
            pk=job.pk,
            user_id=job.user_id,
            account_signature=job.account_signature,
            recipient_email=job.recipient_email,
            attempts=job.attempts,
            lease_expires_at=job.lease_expires_at,
        ),
    )


def _finish(claim: ClaimedResetJob, **changes) -> None:
    """Change state only when the original lease remains current."""
    PasswordResetEmailJob.objects.filter(
        pk=claim.pk,
        status=PasswordResetEmailJob.Status.PROCESSING,
        lease_expires_at=claim.lease_expires_at,
    ).update(**changes)


def _retry_or_fail(
    claim: ClaimedResetJob, error_code: str
) -> DeliveryOutcome:
    """Use the same bounded exponential backoff as verification email."""
    if claim.attempts >= MAX_DELIVERY_ATTEMPTS:
        _finish(
            claim, status=PasswordResetEmailJob.Status.FAILED,
            lease_expires_at=None, last_error_code=error_code,
        )
        return DeliveryOutcome.FAILED
    _finish(
        claim,
        status=PasswordResetEmailJob.Status.PENDING,
        lease_expires_at=None,
        available_at=timezone.now() + RETRY_DELAYS[claim.attempts - 1],
        last_error_code=error_code,
    )
    return DeliveryOutcome.RETRY


def _deliver(claim: ClaimedResetJob, user: User, origin: str):
    """Render and send while keeping token data out of stored job rows."""
    try:
        reset_url = origin + password_reset_path_for_user(user)
        message = build_password_reset_message(
            recipient=claim.recipient_email, reset_url=reset_url,
        )
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error(
            "password_reset.preparation_failed job_id=%s error_type=%s",
            claim.pk, type(exc).__name__,
        )
        return _retry_or_fail(claim, "preparation")
    try:
        send_email_message(message)
    except (OSError, SMTPException):
        return _retry_or_fail(claim, "transport")
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.error(
            "password_reset.delivery_failed job_id=%s error_type=%s",
            claim.pk, type(exc).__name__,
        )
        return _retry_or_fail(claim, "delivery")
    mark_email_job_sent(claim, _finish, PasswordResetEmailJob.Status.SENT)
    return DeliveryOutcome.SENT


def deliver_next_password_reset_email(origin: str):
    """Deliver a reset job only if the recipient and account still match."""
    public_origin = validate_public_origin(origin)
    claim = claim_password_reset_job()
    if claim is None:
        return None
    user = claimed_email_user(
        claim, _finish, PasswordResetEmailJob.Status.CANCELLED
    )
    if user is None:
        return DeliveryOutcome.CANCELLED
    if (
        not password_reset_eligible(user)
        or user.email.casefold() != claim.recipient_email.casefold()
        or not constant_time_compare(
            claim.account_signature, account_state_signature(user)
        )
    ):
        _finish(
            claim, status=PasswordResetEmailJob.Status.CANCELLED,
            lease_expires_at=None, last_error_code="outdated_account",
        )
        return DeliveryOutcome.CANCELLED
    return _deliver(claim, user, public_origin)
