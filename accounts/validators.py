"""Validation rules for Aether account identifiers."""

from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


USERNAME_PATTERN = (
    r"^[A-Za-z0-9](?:[A-Za-z0-9._-]{1,30})[A-Za-z0-9]$"
)

username_validator = RegexValidator(
    regex=USERNAME_PATTERN,
    message=_(
        "Enter a username 3–32 characters long using only ASCII letters, "
        "digits, periods, underscores, and hyphens. The username must start "
        "and end with a letter or digit."
    ),
    code="invalid_username",
)
