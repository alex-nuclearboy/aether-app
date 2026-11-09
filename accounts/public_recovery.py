"""Public recovery operations for unverified registration accounts."""

from django.contrib.auth import check_password_with_timing_attack_mitigation
from django.db import IntegrityError, transaction
from django.views.decorators.debug import sensitive_variables

from accounts.email_outbox import (
    VerificationQueueStatus,
    queue_verification_email,
)
from accounts.models import User, VerificationEmailJob


@transaction.atomic
def request_public_verification_resend(email: str) -> None:
    """Queue for an eligible address without disclosing its existence.

    Lock the account before comparing the address and enqueuing. A
    correction running concurrently cannot redirect this request to
    an address other than the one submitted by the visitor.
    """
    user = (
        User.objects.select_for_update()
        .filter(
            email__iexact=email,
            email_verification_required=True,
            is_active=True,
        )
        .first()
    )
    if user is not None and not user.is_email_verified:
        queue_verification_email(user.pk)

_EMAIL_UNIQUE_CONSTRAINTS = {
    "accounts_user_email_key",
    "accounts_user_email_ci_unique",
}


@sensitive_variables("password")
def correct_unverified_registration_email(
    username: str, password: str, new_email: str
) -> bool:
    """Atomically change a never-verified public account's email.

    Return a neutral result for unknown or ineligible accounts, incorrect
    passwords and duplicate recipient addresses. Never send SMTP in HTTP.
    """
    try:
        with transaction.atomic():
            user = (
                User.objects.select_for_update()
                .filter(username__iexact=username)
                .first()
            )
            if not check_password_with_timing_attack_mitigation(
                user, password
            ):
                return False

            if (
                not user.is_active
                or not user.email_verification_required
                or user.verified_email
                or user.is_staff
                or user.is_superuser
            ):
                return False
            if user.email.casefold() == new_email.casefold():
                return False

            user.email = new_email
            user.verified_email = ""
            user.email_verification_sent_at = None
            user.save(
                update_fields=[
                    "email", "verified_email", "email_verification_sent_at"
                ]
            )
            VerificationEmailJob.objects.filter(
                user=user,
                status__in=[
                    VerificationEmailJob.Status.PENDING,
                    VerificationEmailJob.Status.PROCESSING,
                ],
            ).update(
                status=VerificationEmailJob.Status.CANCELLED,
                lease_expires_at=None,
                last_error_code="email_changed",
            )
            if queue_verification_email(user.pk) != (
                VerificationQueueStatus.QUEUED
            ):
                raise RuntimeError("Corrected-address email was not queued.")
    except IntegrityError as exc:
        diagnostic = getattr(exc.__cause__, "diag", None)
        constraint = getattr(diagnostic, "constraint_name", None)
        if constraint not in _EMAIL_UNIQUE_CONSTRAINTS:
            raise
        return False

    return True
