"""Tests for Aether user models."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction

from accounts.models import User


def test_configured_user_model_is_accounts_user() -> None:
    """Use the project-specific accounts user model."""
    assert get_user_model() is User


def test_user_keeps_username_as_primary_identifier() -> None:
    """Keep username as Django's primary authentication identifier."""
    assert User.USERNAME_FIELD == "username"


def test_username_has_expected_maximum_length() -> None:
    """Limit Aether usernames to 32 characters."""
    username_field = User._meta.get_field("username")

    assert username_field.max_length == 32


@pytest.mark.django_db
def test_user_can_be_created_with_valid_identifiers() -> None:
    """Create an Aether user with valid account identifiers."""
    user = User.objects.create_user(
        username="aether-user",
        email="aether.user@example.com",
        password="test-password",
    )

    assert user.username == "aether-user"
    assert user.email == "aether.user@example.com"
    assert user.check_password("test-password")


@pytest.mark.django_db
def test_database_rejects_invalid_username() -> None:
    """Enforce username syntax at the database boundary."""
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(
            username="aether@user",
            email="invalid-username@example.com",
            password="test-password",
        )


@pytest.mark.django_db
def test_username_must_be_unique_case_insensitively() -> None:
    """Reject usernames that differ only by letter case."""
    User.objects.create_user(
        username="Aether.User",
        email="first-user@example.com",
        password="test-password",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(
            username="aether.user",
            email="second-user@example.com",
            password="test-password",
        )


@pytest.mark.django_db
def test_email_must_be_unique_case_insensitively() -> None:
    """Reject email addresses that differ only by letter case."""
    User.objects.create_user(
        username="first-user",
        email="Account@example.com",
        password="test-password",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create_user(
            username="second-user",
            email="account@example.com",
            password="test-password",
        )


@pytest.mark.django_db
@pytest.mark.parametrize("email", ["", " ", "   "])
def test_database_rejects_blank_email(
    email: str,
) -> None:
    """Reject blank emails even when the manager is bypassed."""
    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.create(
            username="test-member",
            email=email,
        )


@pytest.mark.django_db
@pytest.mark.parametrize("email", ["", " ", "   "])
def test_database_rejects_blank_email_update(
    email: str,
) -> None:
    """Enforce the email constraint during direct updates."""
    user = User.objects.create_user(
        username="test-member",
        email="member@example.com",
        password="test-password",
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        User.objects.filter(pk=user.pk).update(email=email)

    user.refresh_from_db()
    assert user.email == "member@example.com"


@pytest.mark.django_db
def test_new_user_email_is_not_verified() -> None:
    """New accounts start without a verified email address."""
    user = User.objects.create_user(
        username="test-member",
        email="member@example.com",
        password="test-password",
    )

    assert user.verified_email == ""
    assert user.is_email_verified is False


@pytest.mark.django_db
def test_current_email_can_be_marked_as_verified() -> None:
    """Persist verification of the user's current email address."""
    user = User.objects.create_user(
        username="test-member",
        email="member@example.com",
        password="test-password",
    )
    user.verified_email = user.email
    user.save(update_fields=["verified_email"])
    user.refresh_from_db()

    assert user.verified_email == "member@example.com"
    assert user.is_email_verified is True


@pytest.mark.django_db
def test_verified_email_comparison_is_case_insensitive() -> None:
    """Compare verified addresses using the account email policy."""
    user = User.objects.create_user(
        username="test-member",
        email="Member@example.com",
        password="test-password",
    )
    user.verified_email = "member@EXAMPLE.COM"

    assert user.is_email_verified is True


@pytest.mark.django_db
def test_email_change_invalidates_current_verification() -> None:
    """Do not treat a changed email as verified, even after ORM updates."""
    user = User.objects.create_user(
        username="test-member",
        email="old@example.com",
        password="test-password",
    )
    user.verified_email = user.email
    user.save(update_fields=["verified_email"])

    User.objects.filter(pk=user.pk).update(email="new@example.com")
    user.refresh_from_db()

    assert user.verified_email == "old@example.com"
    assert user.is_email_verified is False


@pytest.mark.django_db
def test_verification_does_not_activate_an_inactive_user() -> None:
    """Keep email ownership independent of account activation status."""
    user = User.objects.create_user(
        username="test-member",
        email="member@example.com",
        password="test-password",
        is_active=False,
    )
    user.verified_email = user.email
    user.save(update_fields=["verified_email"])
    user.refresh_from_db()

    assert user.is_email_verified is True
    assert user.is_active is False


def test_verified_email_is_not_directly_editable() -> None:
    """Exclude the verification marker from ordinary model forms."""
    field = User._meta.get_field("verified_email")

    assert field.editable is False
