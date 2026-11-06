"""Public recovery operations for unverified registration accounts."""

from django.db import transaction

from accounts.email_outbox import queue_verification_email
from accounts.models import User


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
