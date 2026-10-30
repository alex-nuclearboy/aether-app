"""Transactional registration persistence and uniqueness-race tests."""

from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from accounts.forms import AetherRegistrationForm
from accounts.models import User
from accounts.registration import create_registration_user
from accounts.tests.registration_helpers import registration_data

pytestmark = pytest.mark.django_db


def registration_form(**overrides):
    """Return an already validated form for the registration service."""
    form = AetherRegistrationForm(registration_data(**overrides))
    assert form.is_valid(), form.errors.as_data()
    return form


def test_create_registration_user_persists_pending_account():
    """Persist secure password hash, verified state, and login policy."""
    form = registration_form()

    user = create_registration_user(form)
    user.refresh_from_db()

    assert user.username == "test-member"
    assert user.email == "member@example.com"
    assert user.check_password("Safer-Test-Passphrase-729!")
    assert user.email_verification_required is True
    assert user.verified_email == ""
    assert user.is_email_verified is False
    assert user.is_active is True


@pytest.mark.parametrize(
    ("conflict_field", "existing_username", "existing_email"),
    [
        ("username", "TEST-MEMBER", "other@example.com"),
        ("username", "test-member", "other@example.com"),
        ("email", "other-member", "MEMBER@EXAMPLE.COM"),
    ],
)
def test_duplicate_created_after_form_validation_is_field_error(
    conflict_field, existing_username, existing_email
):
    """Map a real PostgreSQL uniqueness race to the correct form field."""
    form = registration_form()
    User.objects.create_user(
        username=existing_username,
        email=existing_email,
        password="Other-Safer-Passphrase-809!",
    )

    with pytest.raises(ValidationError) as error:
        create_registration_user(form)

    assert conflict_field in error.value.error_dict
    assert error.value.error_dict[conflict_field][0].code == "unique"
    assert User.objects.count() == 1

    # Future registration views can render the error beside its input.
    form.add_error(None, error.value)
    assert conflict_field in form.errors
    assert form.errors.as_data()[conflict_field][0].code == "unique"


def test_ordinary_email_uniqueness_violation_is_caught():
    """Catch exact-case duplicates, not only the functional unique index."""
    form = registration_form()
    User.objects.create_user(
        username="another-member",
        email="member@example.com",
        password="Other-Safer-Passphrase-809!",
    )

    with pytest.raises(ValidationError) as error:
        create_registration_user(form)

    assert error.value.error_dict["email"][0].code == "unique"


def test_service_rejects_invalid_form_without_writing():
    """Do not save data that failed form validation."""
    form = AetherRegistrationForm(
        {"username": "test-member", "email": "invalid"}
    )

    with pytest.raises(ValueError, match="must be valid"):
        create_registration_user(form)

    assert not User.objects.exists()


def test_unrelated_database_error_is_not_misreported_as_duplicate():
    """Unknown integrity failures must not be disguised as form errors."""
    form = registration_form()

    with patch.object(User, "save", side_effect=IntegrityError("other")):
        with pytest.raises(IntegrityError, match="other"):
            create_registration_user(form)

    assert not User.objects.exists()
