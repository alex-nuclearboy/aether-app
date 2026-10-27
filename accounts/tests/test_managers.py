"""Tests for the Aether user manager."""

import pytest
from asgiref.sync import async_to_sync
from django.core.exceptions import ValidationError

from accounts.managers import AetherUserManager
from accounts.models import User


def test_user_uses_custom_manager() -> None:
    """Use the Aether manager for account creation."""
    assert isinstance(User.objects, AetherUserManager)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "method_name",
    ["create_user", "create_superuser"],
)
@pytest.mark.parametrize(
    "email",
    [None, "", " ", "invalid-email", "member@", "a" * 255],
)
def test_creation_rejects_invalid_email(
    method_name: str,
    email: str | None,
) -> None:
    """Reject missing, malformed, and excessively long emails."""
    create = getattr(User.objects, method_name)

    with pytest.raises(ValidationError):
        create(
            username="test-member",
            email=email,
            password="test-password",
        )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "method_name",
    ["create_user", "create_superuser"],
)
def test_creation_normalizes_email(
    method_name: str,
) -> None:
    """Strip whitespace and normalize the email domain."""
    create = getattr(User.objects, method_name)

    user = create(
        username="test-member",
        email=" Member@EXAMPLE.COM ",
        password="test-password",
    )

    assert user.email == "Member@example.com"
    assert user.check_password("test-password")


@pytest.mark.django_db
def test_create_superuser_preserves_permissions() -> None:
    """Preserve Django's standard superuser privileges."""
    user = User.objects.create_superuser(
        username="test-admin",
        email="admin@example.com",
        password="test-password",
    )

    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "method_name",
    ["acreate_user", "acreate_superuser"],
)
@pytest.mark.parametrize(
    "email",
    [None, "", "invalid-email"],
)
def test_async_creation_rejects_invalid_email(
    method_name: str,
    email: str | None,
) -> None:
    """Apply the same email validation in async creation."""
    create = getattr(User.objects, method_name)

    with pytest.raises(ValidationError):
        async_to_sync(create)(
            username="test-member",
            email=email,
            password="test-password",
        )


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "method_name",
    ["acreate_user", "acreate_superuser"],
)
def test_async_creation_normalizes_email(
    method_name: str,
) -> None:
    """Normalize email addresses in asynchronous creation."""
    create = getattr(User.objects, method_name)

    user = async_to_sync(create)(
        username="test-member",
        email="Member@EXAMPLE.COM",
        password="test-password",
    )

    assert user.email == "Member@example.com"
    assert user.check_password("test-password")
