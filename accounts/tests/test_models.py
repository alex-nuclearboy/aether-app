"""Tests for Aether user models."""

import pytest
from django.contrib.auth import get_user_model
from django.db import IntegrityError

from accounts.models import User


def test_configured_user_model_is_accounts_user() -> None:
    """Use the project-specific accounts user model."""
    assert get_user_model() is User


def test_user_keeps_username_as_primary_identifier() -> None:
    """Keep username as Django's primary authentication identifier."""
    assert User.USERNAME_FIELD == "username"


@pytest.mark.django_db
def test_user_can_be_created_with_username_and_email() -> None:
    """Create an Aether user with the required identity fields."""
    user = User.objects.create_user(
        username="test",
        email="test@example.com",
        password="test-password",
    )

    assert user.username == "test"
    assert user.email == "test@example.com"
    assert user.check_password("test-password")


@pytest.mark.django_db
def test_user_email_must_be_unique() -> None:
    """Reject duplicate user email addresses."""
    User.objects.create_user(
        username="first-user",
        email="shared@example.com",
        password="test-password",
    )

    with pytest.raises(IntegrityError):
        User.objects.create_user(
            username="second-user",
            email="shared@example.com",
            password="test-password",
        )
