"""User models for the Aether accounts application."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower

from accounts.validators import USERNAME_PATTERN, username_validator


class User(AbstractUser):
    """Aether user account."""

    username = models.CharField(
        "username",
        max_length=32,
        unique=True,
        help_text=(
            "Required. 3–32 characters. ASCII letters, digits, periods, "
            "underscores, and hyphens only. Must start and end with a "
            "letter or digit."
        ),
        validators=[username_validator],
        error_messages={
            "unique": "A user with that username already exists.",
        },
    )

    email = models.EmailField(
        "email address",
        unique=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(
                    username__regex=USERNAME_PATTERN,
                ),
                name="accounts_user_username_format",
                violation_error_message="Enter a valid username.",
            ),
            models.UniqueConstraint(
                Lower("username"),
                name="accounts_user_username_ci_unique",
                violation_error_message=(
                    "A user with that username already exists."
                ),
            ),
            models.UniqueConstraint(
                Lower("email"),
                name="accounts_user_email_ci_unique",
                violation_error_message=(
                    "A user with that email address already exists."
                ),
            ),
        ]
