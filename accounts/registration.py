"""Transactional account creation for future public registration views."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from accounts.forms import AetherRegistrationForm
from accounts.models import User

# PostgreSQL reports the violated constraint through the driver diagnostic.
# Both field-level uniqueness and the case-insensitive unique indexes apply.
_UNIQUE_FIELDS = {
    "accounts_user_username_key": "username",
    "accounts_user_username_ci_unique": "username",
    "accounts_user_email_key": "email",
    "accounts_user_email_ci_unique": "email",
}


def create_registration_user(form: AetherRegistrationForm) -> User:
    """Create a pending account, translating known unique-key races.

    The caller must attach a field-specific ValidationError to the form
    if a conflict occurs. Other database errors remain visible to the caller.
    """
    if not form.is_valid():
        raise ValueError("Registration form must be valid before saving.")

    user = form.save(commit=False)

    try:
        with transaction.atomic():
            user.save()
    except IntegrityError as exc:
        diagnostic = getattr(exc.__cause__, "diag", None)
        constraint = getattr(diagnostic, "constraint_name", None)
        field = _UNIQUE_FIELDS.get(constraint)
        if field is None:
            raise

        raise ValidationError(
            {
                field: ValidationError(
                    User._meta.get_field(field).error_messages["unique"],
                    code="unique",
                ),
            }
        ) from exc

    return user
