
"""Render account verification emails for the outbox worker."""

from datetime import timedelta

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext as _

from accounts.models import User
from accounts.tokens import email_verification_token


VERIFICATION_EMAIL_COOLDOWN = timedelta(minutes=1)


def verification_path_for_user(user: User) -> str:
    """Build a fresh confirmation path for the user's current state."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = email_verification_token.make_token(user)
    return reverse(
        "email_verification_confirm",
        kwargs={"uidb64": uidb64, "token": token},
    )


def build_verification_message(
    *, recipient: str, verification_url: str
) -> EmailMultiAlternatives:
    """Render the existing plain-text and HTML verification templates."""
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
    return message
