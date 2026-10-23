"""Authentication audit events for Aether."""

import logging
from datetime import UTC
from math import ceil

from axes.helpers import get_cool_off
from axes.signals import user_locked_out
from django.conf import settings
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.utils import timezone
from django.utils.crypto import salted_hmac

from accounts.lockouts import get_lockout_deadline
from infrastructure.request import get_client_ip


logger = logging.getLogger("aether.audit")


def _identifier_fingerprint(identifier):
    """Create a keyed fingerprint of a login identifier."""
    return salted_hmac(
        "aether.authentication.lockout",
        identifier.casefold(),
        algorithm="sha256",
    ).hexdigest()


@receiver(
    user_logged_in,
    dispatch_uid="accounts.audit.login_success",
)
def audit_login_success(*, request, user, **_kwargs):
    """Record a successful authentication event."""
    logger.info(
        "authentication.login_success user_id=%s client_ip=%s",
        user.pk,
        get_client_ip(request),
    )


@receiver(
    user_logged_out,
    dispatch_uid="accounts.audit.logout",
)
def audit_logout(*, request, user, **_kwargs):
    """Record an authenticated user's logout."""
    if user is not None:
        logger.info(
            "authentication.logout user_id=%s client_ip=%s",
            user.pk,
            get_client_ip(request),
        )


@receiver(
    user_locked_out,
    dispatch_uid="accounts.audit.lockout",
)
def audit_lockout(*, request, username, **_kwargs):
    """Record a newly triggered authentication lockout."""
    failures = getattr(request, "axes_failures_since_start", None)

    if failures != settings.AXES_FAILURE_LIMIT or not username:
        return

    cool_off = get_cool_off(request)
    deadline = get_lockout_deadline(request, username)

    if cool_off is None or deadline is None:
        return

    remaining = max(
        0,
        ceil((deadline - timezone.now()).total_seconds()),
    )

    logger.warning(
        "authentication.lockout identifier_hash=%s "
        "client_ip=%s failures=%s duration_seconds=%s "
        'retry_after_seconds=%s locked_until="%s"',
        _identifier_fingerprint(username),
        get_client_ip(request),
        failures,
        int(cool_off.total_seconds()),
        remaining,
        deadline.astimezone(UTC).isoformat(
            sep=" ",
            timespec="seconds",
        ),
    )
