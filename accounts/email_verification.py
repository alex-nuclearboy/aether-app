"""Server-side verification of an Aether user's current email address."""

from django.db import transaction

from accounts.models import User
from accounts.tokens import email_verification_token


def verify_email(user_id: int, token: str) -> bool:
    """Verify a valid token once, without changing account activation."""
    with transaction.atomic():
        user = User.objects.select_for_update().filter(pk=user_id).first()

        if user is None or user.is_email_verified:
            return False

        if not email_verification_token.check_token(user, token):
            return False

        user.verified_email = user.email
        user.save(update_fields=["verified_email"])
        return True
