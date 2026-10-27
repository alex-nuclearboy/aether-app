"""User models for the Aether accounts application."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils.translation import gettext_lazy as _

from accounts.managers import AetherUserManager
from accounts.validators import USERNAME_PATTERN, username_validator


class User(AbstractUser):
    """Aether user account."""

    objects = AetherUserManager()

    username = models.CharField(
        _("username"),
        max_length=32,
        unique=True,
        help_text=_(
            "Required. 3–32 characters. ASCII letters, digits, periods, "
            "underscores, and hyphens only. Must start and end with a "
            "letter or digit."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )

    email = models.EmailField(
        _("email address"),
        unique=True,
        error_messages={
            "unique": _("A user with that email address already exists."),
        },
    )

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    username__regex=USERNAME_PATTERN,
                ),
                name="accounts_user_username_format",
                violation_error_message=_("Enter a valid username."),
            ),
            models.CheckConstraint(
                condition=models.Q(
                    email__regex=r"[^[:space:]]",
                ),
                name="accounts_user_email_not_blank",
                violation_error_message=_(
                    "An email address is required."
                ),
            ),
            models.UniqueConstraint(
                Lower("username"),
                name="accounts_user_username_ci_unique",
                violation_error_message=_(
                    "A user with that username already exists."
                ),
            ),
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
                violation_error_message=_(
                    "A user with that email address already exists."
                ),
            ),
        ]
