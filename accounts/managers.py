"""User managers for the Aether accounts application."""

from django.contrib.auth.models import UserManager
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class AetherUserManager(UserManager):
    """Enforce valid email addresses when creating accounts."""

    def _validate_email(self, email: str | None) -> str:
        """Validate an email using the configured model field."""
        if not isinstance(email, str) or not email.strip():
            raise ValidationError(
                _("An email address is required."),
                code="required",
            )

        return self.model._meta.get_field("email").clean(
            email.strip(),
            None,
        )

    def create_user(
        self, username, email=None, password=None, **extra_fields
    ):
        """Create a user with a valid email address."""
        return super().create_user(
            username,
            self._validate_email(email),
            password,
            **extra_fields,
        )

    async def acreate_user(
        self, username, email=None, password=None, **extra_fields
    ):
        """Asynchronously create a user with a valid email."""
        return await super().acreate_user(
            username,
            self._validate_email(email),
            password,
            **extra_fields,
        )

    def create_superuser(
        self, username, email=None, password=None, **extra_fields
    ):
        """Create a superuser with a valid email address."""
        return super().create_superuser(
            username,
            self._validate_email(email),
            password,
            **extra_fields,
        )

    async def acreate_superuser(
        self, username, email=None, password=None, **extra_fields
    ):
        """Asynchronously create a superuser with a valid email."""
        return await super().acreate_superuser(
            username,
            self._validate_email(email),
            password,
            **extra_fields,
        )
