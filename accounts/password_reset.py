"""Privacy-preserving requests for password reset email delivery."""

from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from accounts.models import PasswordResetEmailJob, User


RESET_REQUEST_COOLDOWN = timedelta(minutes=1)


def password_reset_eligible(user: User | None) -> bool:
    """Allow reset only for active users with trusted email ownership."""
    return bool(
        user is not None
        and user.is_active
        and user.has_usable_password()
        and (not user.email_verification_required or user.is_email_verified)
    )


def account_state_signature(user: User) -> str:
    """Bind queued work to the password and email state at request time."""
    last_login = user.last_login.isoformat() if user.last_login else ""
    return salted_hmac(
        "accounts.password_reset.state.v1",
        f"{user.pk}\0{user.password}\0{user.email.casefold()}"
        f"\0{last_login}",
        algorithm="sha256",
    ).hexdigest()


@transaction.atomic
def request_password_reset_email(email: str) -> None:
    """Queue one eligible message without revealing account membership."""
    user = (
        User.objects.select_for_update()
        .filter(email__iexact=email)
        .first()
    )
    if not password_reset_eligible(user):
        return

    active = [
        PasswordResetEmailJob.Status.PENDING,
        PasswordResetEmailJob.Status.PROCESSING,
    ]
    if PasswordResetEmailJob.objects.filter(
        user=user, recipient_email__iexact=user.email,
        status__in=active,
    ).exists():
        return

    last_job = (
        PasswordResetEmailJob.objects.filter(user=user)
        .order_by("-created_at", "-pk")
        .first()
    )
    now = timezone.now()
    if last_job and now - last_job.created_at < RESET_REQUEST_COOLDOWN:
        return

    PasswordResetEmailJob.objects.create(
        user=user,
        recipient_email=user.email,
        account_signature=account_state_signature(user),
        available_at=now,
    )
