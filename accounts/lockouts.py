"""Authentication lockout helpers for Aether accounts."""


from datetime import datetime
from math import ceil

from axes.helpers import get_cool_off
from axes.models import AccessAttempt
from django.conf import settings
from django.db.models import Max, Sum
from django.http import HttpRequest
from django.utils import timezone

from accounts.models import User
from infrastructure.request import get_client_ip


def get_lockout_username(
    request: HttpRequest,
    credentials: dict | None = None,
) -> str:
    """Resolve username and email aliases to a common lockout identity."""
    if credentials is not None:
        identifier = credentials.get("username")
    else:
        identifier = request.POST.get("username")

    if not isinstance(identifier, str):
        return ""

    if "@" in identifier:
        username = (
            User.objects.filter(email__iexact=identifier)
            .values_list("username", flat=True)
            .first()
        )

        if username is not None:
            return username.casefold()

    return identifier.casefold()


def get_lockout_deadline(
    request: HttpRequest,
    identifier: str,
) -> datetime | None:
    """Return the deadline for an active username/IP lockout."""
    if not identifier:
        return None

    cool_off = get_cool_off(request)
    client_ip = get_client_ip(request)

    if cool_off is None or client_ip is None:
        return None

    username = get_lockout_username(
        request,
        {"username": identifier},
    )

    if not username:
        return None

    now = timezone.now()

    attempts = AccessAttempt.objects.filter(
        username=username,
        ip_address=client_ip,
        attempt_time__gt=now - cool_off,
    )

    summary = attempts.aggregate(
        failures=Sum("failures_since_start"),
        last_attempt=Max("attempt_time"),
    )

    if (summary["failures"] or 0) < settings.AXES_FAILURE_LIMIT:
        return None

    return summary["last_attempt"] + cool_off


def get_lockout_remaining_seconds(
    request: HttpRequest,
    identifier: str,
) -> int:
    """Return the remaining lockout time in whole seconds."""
    deadline = get_lockout_deadline(request, identifier)

    if deadline is None:
        return 0

    remaining = (deadline - timezone.now()).total_seconds()

    return max(0, ceil(remaining))
