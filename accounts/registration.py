"""Transactional account creation for staged public registration."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from accounts.email_outbox import (
    VerificationQueueStatus,
    queue_verification_email,
)
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
    """Persist a pending account and its email job in one transaction.

    Map known PostgreSQL uniqueness races to field errors. Other database
    failures, including outbox failures, roll back the account creation.
    """
    if not form.is_valid():
        raise ValueError("Registration form must be valid before saving.")

    user = form.save(commit=False)

    try:
        with transaction.atomic():
            user.save()
            status = queue_verification_email(user.pk)
            if status != VerificationQueueStatus.QUEUED:
                raise RuntimeError("Registration email was not queued.")
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
