"""Delivery of account email verification links."""

from datetime import timedelta
from enum import StrEnum

from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.http import HttpRequest
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _

from accounts.models import User
from accounts.tokens import email_verification_token


VERIFICATION_EMAIL_COOLDOWN = timedelta(minutes=1)


class VerificationEmailStatus(StrEnum):
    """Outcomes of a verification-email request."""

    SENT = "sent"
    VERIFIED = "verified"
    TOO_SOON = "too_soon"


def send_verification_email(
    request: HttpRequest,
    user_id: int,
) -> VerificationEmailStatus:
    """Send one link to the current email, with a database-backed cooldown.

    The row lock reserves a send slot before contacting SMTP; external I/O
    runs outside the transaction. A failed delivery releases that slot.
    """
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=user_id)

        if user.is_email_verified:
            return VerificationEmailStatus.VERIFIED

        sent_at = user.email_verification_sent_at
        now = timezone.now()
        if sent_at and now - sent_at < VERIFICATION_EMAIL_COOLDOWN:
            return VerificationEmailStatus.TOO_SOON

        user.email_verification_sent_at = now
        user.save(update_fields=["email_verification_sent_at"])

        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = email_verification_token.make_token(user)
        recipient = user.email

    verification_path = reverse(
        "email_verification_confirm",
        kwargs={"uidb64": uidb64, "token": token},
    )
    verification_url = request.build_absolute_uri(verification_path)
    context = {"verification_url": verification_url}

    message = EmailMultiAlternatives(
        subject=_("Verify your Aether email address"),
        body=render_to_string(
            "accounts/email/verification.txt", context
        ),
        to=[recipient],
    )
    message.attach_alternative(
        render_to_string("accounts/email/verification.html", context),
        "text/html",
    )

    try:
        delivered = message.send()
        if delivered != 1:
            raise OSError("Email backend did not accept the message.")
    except Exception:  # pylint: disable=broad-exception-caught
        # Compare-and-swap: never clear a reservation made by a later send.
        User.objects.filter(
            pk=user_id,
            email_verification_sent_at=now,
        ).update(email_verification_sent_at=sent_at)
        raise

    return VerificationEmailStatus.SENT
