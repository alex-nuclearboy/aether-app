"""Database-backed request limits for future public account endpoints."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from django.db import transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from accounts.models import PublicRequestCounter


class PublicRequestAction(StrEnum):
    """Distinguish registration, resend and email-correction limits."""

    REGISTER_IP = "register.ip"
    RESEND_IP = "resend.ip"
    RESEND_EMAIL = "resend.email"
    RESET_PASSWORD_IP = "reset_password.ip"
    RESET_PASSWORD_EMAIL = "reset_password.email"
    CORRECT_EMAIL_IP = "correct_email.ip"
    CORRECT_EMAIL_USERNAME = "correct_email.username"


@dataclass(frozen=True)
class RequestLimit:
    """Set the request allowance within a fixed UTC time window."""

    attempts: int
    window: timedelta


PUBLIC_REQUEST_LIMITS = {
    PublicRequestAction.REGISTER_IP: RequestLimit(10, timedelta(hours=1)),
    PublicRequestAction.RESEND_IP: RequestLimit(10, timedelta(hours=1)),
    PublicRequestAction.RESEND_EMAIL: RequestLimit(3, timedelta(hours=1)),
    PublicRequestAction.RESET_PASSWORD_IP: RequestLimit(
        10, timedelta(hours=1)
    ),
    PublicRequestAction.RESET_PASSWORD_EMAIL: RequestLimit(
        3, timedelta(hours=1)
    ),
    PublicRequestAction.CORRECT_EMAIL_IP: RequestLimit(10, timedelta(hours=1)),
    PublicRequestAction.CORRECT_EMAIL_USERNAME: RequestLimit(
        5, timedelta(hours=1)
    ),
}


def consume_public_request(
    action: PublicRequestAction,
    identity: str,
    *,
    now: datetime | None = None,
) -> bool:
    """Atomically consume one allowance without storing the identity.

    Return ``False`` when the current window is exhausted. Callers must
    resolve and validate client identities before calling this function.
    """
    if not isinstance(action, PublicRequestAction):
        raise ValueError("An existing public request action is required.")
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError("A non-empty request identity is required.")

    policy = PUBLIC_REQUEST_LIMITS[action]
    current_time = now if now is not None else timezone.now()
    if timezone.is_naive(current_time):
        raise ValueError("The request time must be timezone-aware.")

    window_seconds = int(policy.window.total_seconds())
    window_number = int(current_time.timestamp()) // window_seconds
    window_end = datetime.fromtimestamp(
        (window_number + 1) * window_seconds,
        tz=UTC,
    )
    fingerprint = salted_hmac(
        "aether.public_request_limits.v1",
        f"{action.value}\0{identity.strip().casefold()}\0{window_number}",
        algorithm="sha256",
    ).hexdigest()

    with transaction.atomic():
        counter, _ = (
            PublicRequestCounter.objects.select_for_update()
            .get_or_create(
                key=fingerprint,
                defaults={"expires_at": window_end},
            )
        )
        if counter.attempts >= policy.attempts:
            return False
        counter.attempts += 1
        counter.save(update_fields=["attempts"])
        return True


def public_request_retry_after(action: PublicRequestAction) -> int:
    """Return seconds until the next fixed UTC allowance window."""
    window_seconds = int(PUBLIC_REQUEST_LIMITS[action].window.total_seconds())
    return window_seconds - int(timezone.now().timestamp()) % window_seconds
