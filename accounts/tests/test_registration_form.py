"""Validation and account policy tests for public registration forms."""

import pytest
from django.contrib.auth.forms import UserCreationForm
from django.utils.functional import Promise

from accounts.forms import AetherRegistrationForm
from accounts.models import User
from accounts.tests.registration_helpers import registration_data

pytestmark = pytest.mark.django_db



def test_form_inherits_django_password_validation():
    """Keep Django's password comparison and policy validation."""
    form = AetherRegistrationForm()

    assert isinstance(form, UserCreationForm)
    assert set(form.fields) == {
        "username", "email", "password1", "password2"
    }
    assert form.fields["email"].required


def test_valid_registration_normalises_email_domain():
    """Match the existing email manager normalization policy."""
    form = AetherRegistrationForm(
        registration_data(email="Member@EXAMPLE.COM")
    )

    assert form.is_valid(), form.errors.as_data()
    assert form.cleaned_data["email"] == "Member@example.com"


def test_username_rejects_case_insensitive_duplicate():
    """Use Django's inherited case-insensitive username validation."""
    User.objects.create_user(
        username="Test-Member",
        email="already@example.com",
        password="Safer-Test-Passphrase-729!",
    )
    form = AetherRegistrationForm(registration_data())

    assert not form.is_valid()
    assert "username" in form.errors


def test_email_rejects_case_insensitive_duplicate():
    """Report duplicate email at the email field rather than generally."""
    User.objects.create_user(
        username="existing-member",
        email="Member@Example.com",
        password="Safer-Test-Passphrase-729!",
    )
    form = AetherRegistrationForm(registration_data())

    assert not form.is_valid()
    assert form.errors.as_data()["email"][0].code == "unique"
    assert "__all__" not in form.errors


@pytest.mark.parametrize("email", ["", "not-an-email"])
def test_email_requires_valid_format(email):
    """Retain Django EmailField validation and required-field errors."""
    form = AetherRegistrationForm(registration_data(email=email))

    assert not form.is_valid()
    assert "email" in form.errors


def test_rejects_invalid_username_syntax():
    """Apply the existing ASCII username validator from the model."""
    form = AetherRegistrationForm(registration_data(username="invalid@name"))

    assert not form.is_valid()
    assert "username" in form.errors


def test_rejects_password_confirmation_mismatch():
    """Keep Django's standard password-confirmation error code."""
    form = AetherRegistrationForm(
        registration_data(password2="Different-Safe-Passphrase-514!")
    )

    assert not form.is_valid()
    assert form.errors.as_data()["password2"][0].code == "password_mismatch"


@pytest.mark.parametrize(
    ("password", "expected_code"),
    [
        ("short", "password_too_short"),
        ("password", "password_too_common"),
        ("123456789012345", "password_entirely_numeric"),
        ("test-member", "password_too_similar"),
    ],
)
def test_django_password_validator_error_codes(password, expected_code):
    """Use native Django password rules rather than custom translations."""
    form = AetherRegistrationForm(
        registration_data(password1=password, password2=password)
    )

    assert not form.is_valid()
    codes = {error.code for error in form.errors.as_data()["password2"]}
    assert expected_code in codes


def test_registration_sets_verification_requirement_before_save():
    """Prevent future registration views from bypassing the access policy."""
    form = AetherRegistrationForm(registration_data())
    assert form.is_valid(), form.errors.as_data()

    user = form.save(commit=False)

    assert user.pk is None
    assert user.email_verification_required is True
    assert user.verified_email == ""
    assert user.is_active is True
    assert user.check_password("Safer-Test-Passphrase-729!")


def test_registration_form_direct_save_keeps_policy():
    """Keep the verification requirement even with the normal form API."""
    form = AetherRegistrationForm(registration_data())
    assert form.is_valid(), form.errors.as_data()

    user = form.save()
    user.refresh_from_db()

    assert user.email_verification_required is True
    assert not user.is_email_verified


def test_duplicate_email_message_reuses_model_translation():
    """Reuse the lazy model message rather than copying English text."""
    message = User._meta.get_field("email").error_messages["unique"]

    assert isinstance(message, Promise)
