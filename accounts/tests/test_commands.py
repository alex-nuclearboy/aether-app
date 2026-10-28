"""Tests for account-related Django management commands."""

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from accounts.models import User


@pytest.mark.django_db
def test_createsuperuser_command_creates_valid_account(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Create a superuser through Django's non-interactive CLI."""
    monkeypatch.setenv(
        "DJANGO_SUPERUSER_PASSWORD",
        "Secure-Random-Password!7264",
    )

    call_command(
        "createsuperuser",
        interactive=False,
        username="cli-admin",
        email="Member@EXAMPLE.COM",
        verbosity=0,
    )

    user = User.objects.get(username="cli-admin")
    assert user.email == "Member@example.com"
    assert user.check_password("Secure-Random-Password!7264")
    assert user.is_staff is True
    assert user.is_superuser is True
    assert user.is_active is True


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("email", "error_message"),
    [
        ("", "You must use --email"),
        ("invalid-email", "Enter a valid email address"),
    ],
)
def test_createsuperuser_command_rejects_invalid_email(
    monkeypatch: pytest.MonkeyPatch,
    email: str,
    error_message: str,
) -> None:
    """Reject missing and malformed email in non-interactive mode."""
    monkeypatch.delenv("DJANGO_SUPERUSER_EMAIL", raising=False)

    with pytest.raises(CommandError, match=error_message):
        call_command(
            "createsuperuser",
            interactive=False,
            username="cli-admin",
            email=email,
            verbosity=0,
        )

    assert not User.objects.filter(username="cli-admin").exists()
