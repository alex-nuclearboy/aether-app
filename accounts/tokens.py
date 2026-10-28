"""Tokens for verifying Aether account email addresses."""

from django.contrib.auth.tokens import PasswordResetTokenGenerator

from accounts.models import User


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Bind verification tokens to the account and current email state."""

    key_salt = "accounts.tokens.EmailVerificationTokenGenerator"

    def _make_hash_value(self, user: User, timestamp: int) -> str:
        """Invalidate tokens after email, password, or verification changes."""
        return (
            f"{user.pk}:{user.password}:{timestamp}:"
            f"{user.email}:{user.verified_email}"
        )


email_verification_token = EmailVerificationTokenGenerator()
