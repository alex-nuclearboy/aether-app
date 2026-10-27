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
