"""Atomically queue verification emails for later worker delivery."""

from enum import StrEnum

from django.db import transaction
from django.utils import timezone

from accounts.email_verification import locked_unverified_email_user
from accounts.emails import VERIFICATION_EMAIL_COOLDOWN
from accounts.models import VerificationEmailJob


class VerificationQueueStatus(StrEnum):
    """Results of a request to enqueue a verification email."""

    QUEUED = "queued"
    ALREADY_QUEUED = "already_queued"
    VERIFIED = "verified"
    TOO_SOON = "too_soon"


@transaction.atomic
def queue_verification_email(user_id: int) -> VerificationQueueStatus:
    """Reserve one current-address delivery within a database transaction.

    This function never performs SMTP I/O. The worker will render the
    email and generate its token immediately before attempting delivery.
    """
    user = locked_unverified_email_user(user_id)
    if user is None:
        return VerificationQueueStatus.VERIFIED

    if VerificationEmailJob.objects.filter(
        user=user,
        recipient_email__iexact=user.email,
        status__in=[
            VerificationEmailJob.Status.PENDING,
            VerificationEmailJob.Status.PROCESSING,
        ],
    ).exists():
        return VerificationQueueStatus.ALREADY_QUEUED

    now = timezone.now()
    sent_at = user.email_verification_sent_at
    if sent_at and now - sent_at < VERIFICATION_EMAIL_COOLDOWN:
        return VerificationQueueStatus.TOO_SOON

    VerificationEmailJob.objects.create(
        user=user,
        recipient_email=user.email,
        available_at=now,
    )
    user.email_verification_sent_at = now
    user.save(update_fields=["email_verification_sent_at"])

    return VerificationQueueStatus.QUEUED
