"""Tests for email verification tokens and the verification service."""

from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from django.test import override_settings

from accounts.email_verification import verify_email
from accounts.models import User
from accounts.tokens import email_verification_token

pytestmark = pytest.mark.django_db


@pytest.fixture
def user() -> User:
    """Create an account with an unverified email address."""
    return User.objects.create_user(
        username="test-member",
        email="member@example.com",
        password="test-password",
    )


def test_token_is_valid_for_current_email(user: User) -> None:
    """Accept a token for its issuing account and email."""
    token = email_verification_token.make_token(user)

    assert email_verification_token.check_token(user, token)


def test_token_is_not_valid_for_another_user(user: User) -> None:
    """Prevent tokens from being transferred between accounts."""
    other = User.objects.create_user(
        username="other-member",
        email="other@example.com",
        password="test-password",
    )
    token = email_verification_token.make_token(user)

    assert not email_verification_token.check_token(other, token)


def test_token_is_invalid_after_email_change(user: User) -> None:
    """Bind tokens to the email address at issuance."""
    token = email_verification_token.make_token(user)
    user.email = "changed@example.com"
    user.save(update_fields=["email"])

    assert not email_verification_token.check_token(user, token)


def test_token_is_invalid_after_password_change(user: User) -> None:
    """Invalidate outstanding tokens after password changes."""
    token = email_verification_token.make_token(user)
    user.set_password("new-test-password")
    user.save(update_fields=["password"])

    assert not email_verification_token.check_token(user, token)


def test_token_is_invalid_after_verification(user: User) -> None:
    """Make a token unusable after the address is confirmed."""
    token = email_verification_token.make_token(user)
    user.verified_email = user.email
    user.save(update_fields=["verified_email"])

    assert not email_verification_token.check_token(user, token)


def test_malformed_token_is_rejected(user: User) -> None:
    """Reject tokens that cannot be parsed or authenticated."""
    assert not email_verification_token.check_token(user, "invalid-token")


@override_settings(PASSWORD_RESET_TIMEOUT=60)
def test_token_expires(user: User) -> None:
    """Expire tokens according to Django's configured timeout."""
    issued_at = datetime(2026, 10, 28, 12, 0, 0)
    with patch.object(email_verification_token, "_now", return_value=issued_at):
        token = email_verification_token.make_token(user)

    with patch.object(
        email_verification_token,
        "_now",
        return_value=issued_at + timedelta(seconds=61),
    ):
        assert not email_verification_token.check_token(user, token)


def test_verify_email_sets_current_address(user: User) -> None:
    """Persist verification without changing account privileges."""
    token = email_verification_token.make_token(user)

    assert verify_email(user.pk, token)
    user.refresh_from_db()
    assert user.verified_email == "member@example.com"
    assert user.is_email_verified
    assert user.is_active


def test_verify_email_cannot_reuse_token(user: User) -> None:
    """Reject repeated verification with a consumed token."""
    token = email_verification_token.make_token(user)

    assert verify_email(user.pk, token)
    assert not verify_email(user.pk, token)


def test_verify_email_rejects_invalid_token(user: User) -> None:
    """Do not modify the address when token validation fails."""
    assert not verify_email(user.pk, "invalid-token")

    user.refresh_from_db()
    assert user.verified_email == ""


def test_verify_email_rejects_unknown_user(user: User) -> None:
    """Reject tokens presented for a nonexistent account."""
    token = email_verification_token.make_token(user)

    assert not verify_email(user.pk + 100, token)


def test_verify_email_keeps_inactive_user_inactive(user: User) -> None:
    """Email verification must not activate an account."""
    user.is_active = False
    user.save(update_fields=["is_active"])
    token = email_verification_token.make_token(user)

    assert verify_email(user.pk, token)
    user.refresh_from_db()
    assert user.is_email_verified
    assert not user.is_active
