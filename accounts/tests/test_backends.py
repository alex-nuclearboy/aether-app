
"""Tests for the Aether username-or-email authentication backend."""

from unittest.mock import patch

import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth import (
    aauthenticate,
    authenticate,
    check_password_with_timing_attack_mitigation,
)
from django.contrib.auth.models import Group, Permission

from accounts.backends import UsernameOrEmailBackend
from accounts.models import User


TEST_PASSWORD = "test-password"


def create_test_user() -> User:
    """Create an account with mixed-case identifiers."""
    return User.objects.create_user(
        username="Aether.Member",
        email="Aether.Member@example.com",
        password=TEST_PASSWORD,
    )


@pytest.fixture(autouse=True)
def isolate_authentication_backend(settings):
    """Test the custom authentication backend independently of Axes."""
    settings.AUTHENTICATION_BACKENDS = [
        "accounts.backends.UsernameOrEmailBackend",
    ]
    settings.AXES_ENABLED = False


@pytest.mark.django_db
@pytest.mark.parametrize(
    "identifier",
    [
        "Aether.Member",
        "aether.member",
        "AETHER.MEMBER",
        "Aether.Member@example.com",
        "aether.member@example.com",
        "AETHER.MEMBER@EXAMPLE.COM",
    ],
)
def test_authenticates_by_username_or_email(identifier: str) -> None:
    """Accept both identifier types without requiring matching case."""
    user = create_test_user()

    assert authenticate(
        username=identifier,
        password=TEST_PASSWORD,
    ) == user


@pytest.mark.django_db
def test_wrong_password_is_rejected() -> None:
    """Reject an incorrect password."""
    user = create_test_user()

    assert authenticate(
        username=user.username,
        password="wrong-password",
    ) is None


@pytest.mark.django_db
@pytest.mark.parametrize(
    "identifier",
    ["missing-user", "missing@example.com"],
)
def test_unknown_identifier_uses_timing_mitigation(
    identifier: str,
) -> None:
    """Use Django's dummy hashing for unknown identifiers."""
    with patch(
        "accounts.backends.check_password_with_timing_attack_mitigation",
        wraps=check_password_with_timing_attack_mitigation,
    ) as password_check:
        assert authenticate(
            username=identifier,
            password=TEST_PASSWORD,
        ) is None

    password_check.assert_called_once_with(None, TEST_PASSWORD)


@pytest.mark.django_db
def test_inactive_user_is_rejected() -> None:
    """Reject inactive accounts for either identifier."""
    user = create_test_user()
    user.is_active = False
    user.save(update_fields=["is_active"])

    assert authenticate(
        username=user.username,
        password=TEST_PASSWORD,
    ) is None

    assert authenticate(
        username=user.email,
        password=TEST_PASSWORD,
    ) is None


def test_missing_credentials_are_rejected() -> None:
    """Do not authenticate without both required credentials."""
    backend = UsernameOrEmailBackend()

    assert backend.authenticate(
        None, password=TEST_PASSWORD
    ) is None

    assert backend.authenticate(
        None, username="aether.member"
    ) is None

    assert backend.authenticate(
        None, username=None, password=None
    ) is None


@pytest.mark.django_db
def test_group_permissions_are_preserved() -> None:
    """Retain the standard permission machinery from ModelBackend."""
    user = create_test_user()
    group = Group.objects.create(name="Aether Members")

    permission = Permission.objects.get(
        content_type__app_label="accounts",
        codename="view_user",
    )

    group.permissions.add(permission)
    user.groups.add(group)

    authenticated_user = authenticate(
        username=user.email,
        password=TEST_PASSWORD,
    )

    assert authenticated_user is not None
    assert authenticated_user.has_perm("accounts.view_user")


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize(
    "identifier",
    ["aether.member", "AETHER.MEMBER@EXAMPLE.COM"],
)
def test_async_authenticates_by_username_or_email(
    identifier: str,
) -> None:
    """Use the same identifier rules in asynchronous authentication."""
    user = create_test_user()

    assert async_to_sync(aauthenticate)(
        username=identifier,
        password=TEST_PASSWORD,
    ) == user


@pytest.mark.django_db(transaction=True)
def test_async_rejects_invalid_credentials() -> None:
    """Reject unknown, inactive, and invalid async credentials."""
    user = create_test_user()
    user.is_active = False
    user.save(update_fields=["is_active"])

    assert async_to_sync(aauthenticate)(
        username="missing@example.com",
        password=TEST_PASSWORD,
    ) is None

    assert async_to_sync(aauthenticate)(
        username=user.email,
        password=TEST_PASSWORD,
    ) is None

    assert async_to_sync(aauthenticate)(
        username=user.username,
        password="wrong-password",
    ) is None


def test_async_missing_credentials_are_rejected() -> None:
    """Handle missing credentials in the asynchronous backend."""
    backend = UsernameOrEmailBackend()

    assert async_to_sync(backend.aauthenticate)(
        None, password=TEST_PASSWORD
    ) is None

    assert async_to_sync(backend.aauthenticate)(
        None, username="aether.member"
    ) is None
