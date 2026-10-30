"""Shared input builder for registration validation tests."""


def registration_data(**overrides):
    """Build valid registration credentials with selective overrides."""
    data = {
        "username": "test-member",
        "email": "member@example.com",
        "password1": "Safer-Test-Passphrase-729!",
        "password2": "Safer-Test-Passphrase-729!",
    }
    return {**data, **overrides}
