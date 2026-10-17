"""Tests for Aether account identifier validators."""

import pytest
from django.core.exceptions import ValidationError

from accounts.validators import username_validator


@pytest.mark.parametrize(
    "username",
    [
        "aet",
        "aether",
        "Aether.User",
        "aether_user",
        "aether-user",
        "aether2",
        "a" * 32,
    ],
)
def test_username_validator_accepts_supported_usernames(
    username: str,
) -> None:
    """Accept usernames that satisfy the Aether identifier rules."""
    username_validator(username)


@pytest.mark.parametrize(
    "username",
    [
        "ae",
        "a" * 33,
        ".aether",
        "aether.",
        "_aether",
        "aether_",
        "-aether",
        "aether-",
        "aether@user",
        "aether+user",
        "aether user",
        "aether/user",
        "aetheré",
    ],
)
def test_username_validator_rejects_unsupported_usernames(
    username: str,
) -> None:
    """Reject usernames outside the Aether identifier rules."""
    with pytest.raises(ValidationError):
        username_validator(username)
