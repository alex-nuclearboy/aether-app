"""HTTP responses and audit events for denied authentication attempts."""

import logging

from django.conf import settings
from django.http import HttpResponse
from django.utils.translation import gettext as _

from accounts.audit import identifier_fingerprint
from accounts.lockouts import (
    get_lockout_remaining_seconds,
    get_lockout_username,
)
from infrastructure.request import get_client_ip


logger = logging.getLogger("aether.audit")


def lockout_response(request, _original_response, credentials):
    """Return HTTP 429 with the current remaining lockout duration."""
    if isinstance(credentials, dict):
        identifier = credentials.get("username")
    else:
        identifier = None

    if not isinstance(identifier, str):
        identifier = request.POST.get("username", "")

    remaining = get_lockout_remaining_seconds(request, identifier)

    response = HttpResponse(
        _("Too many failed login attempts. Please try again later."),
        status=settings.AXES_HTTP_RESPONSE_CODE,
        content_type="text/plain; charset=utf-8",
    )
    response["Cache-Control"] = "no-store"
    if remaining > 0:
        response["Retry-After"] = str(remaining)

    if (
        request.method == "POST"
        and not getattr(request, "aether_new_lockout", False)
        and remaining > 0
    ):
        username = get_lockout_username(
            request,
            {"username": identifier},
        )
        if username:
            logger.warning(
                "authentication.lockout_denied identifier_hash=%s "
                "client_ip=%s retry_after_seconds=%s",
                identifier_fingerprint(username),
                get_client_ip(request),
                remaining,
            )

    return response
