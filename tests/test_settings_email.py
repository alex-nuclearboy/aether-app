"""Development and production SMTP settings validation tests."""

import pytest

from tests.settings_helpers import (
    VALID_PRODUCTION_OVERRIDES,
    assert_settings_invalid,
    run_settings,
)


@pytest.mark.parametrize(
    "environment",
    [
        "development",
        "test",
    ],
)
def test_settings_use_console_mailer_outside_production(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    """Use the console email backend outside production."""
    loaded_settings = run_settings(
        monkeypatch,
        AETHER_ENVIRONMENT=environment,
    )

    assert loaded_settings["DEFAULT_FROM_EMAIL"] == "test@example.com"
    assert loaded_settings["MAILERS"] == {
        "default": {
            "BACKEND": "django.core.mail.backends.console.EmailBackend",
        },
    }


def test_settings_use_smtp_mailer_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configure the SMTP email backend in production."""
    loaded_settings = run_settings(
        monkeypatch,
        **VALID_PRODUCTION_OVERRIDES,
    )

    assert loaded_settings["DEFAULT_FROM_EMAIL"] == "aether@example.com"
    assert loaded_settings["MAILERS"] == {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {
                "host": "smtp.example.com",
                "port": 587,
                "username": "test-smtp-user",
                "password": "test-smtp-password",
                "use_tls": True,
                "timeout": 10,
            },
        },
    }


def test_settings_preserve_smtp_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserve the SMTP password exactly as configured."""
    production_environment = {
        **VALID_PRODUCTION_OVERRIDES,
        "MAILER_SMTP_PASSWORD": " test-smtp-password ",
    }

    loaded_settings = run_settings(
        monkeypatch,
        **production_environment,
    )

    assert (
        loaded_settings["MAILERS"]["default"]["OPTIONS"]["password"]
        == " test-smtp-password "
    )


@pytest.mark.parametrize(
    ("variable_name", "expected_message"),
    [
        (
            "MAILER_SMTP_HOST",
            "MAILER_SMTP_HOST must not be empty in production",
        ),
        (
            "MAILER_SMTP_USERNAME",
            "MAILER_SMTP_USERNAME must not be empty in production",
        ),
        (
            "MAILER_SMTP_PASSWORD",
            "MAILER_SMTP_PASSWORD must not be empty in production",
        ),
        (
            "DJANGO_DEFAULT_FROM_EMAIL",
            "DJANGO_DEFAULT_FROM_EMAIL must not be empty in production",
        ),
    ],
)
def test_settings_require_production_email_values(
    monkeypatch: pytest.MonkeyPatch,
    variable_name: str,
    expected_message: str,
) -> None:
    """Require essential email configuration in production."""
    production_environment = {
        **VALID_PRODUCTION_OVERRIDES,
        variable_name: "",
    }

    assert_settings_invalid(
        monkeypatch,
        expected_message,
        **production_environment,
    )


def test_settings_reject_whitespace_only_smtp_password(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject an SMTP password containing only whitespace."""
    production_environment = {
        **VALID_PRODUCTION_OVERRIDES,
        "MAILER_SMTP_PASSWORD": "   ",
    }

    assert_settings_invalid(
        monkeypatch,
        "MAILER_SMTP_PASSWORD must not be empty in production",
        **production_environment,
    )


@pytest.mark.parametrize(
    ("variable_name", "value", "expected_message"),
    [
        (
            "MAILER_SMTP_PORT",
            "0",
            "MAILER_SMTP_PORT must be greater than zero",
        ),
        (
            "MAILER_SMTP_PORT",
            "-1",
            "MAILER_SMTP_PORT must be greater than zero",
        ),
        (
            "MAILER_SMTP_TIMEOUT",
            "0",
            "MAILER_SMTP_TIMEOUT must be greater than zero",
        ),
        (
            "MAILER_SMTP_TIMEOUT",
            "-1",
            "MAILER_SMTP_TIMEOUT must be greater than zero",
        ),
    ],
)
def test_settings_reject_invalid_production_email_numbers(
    monkeypatch: pytest.MonkeyPatch,
    variable_name: str,
    value: str,
    expected_message: str,
) -> None:
    """Reject non-positive SMTP port and timeout values."""
    production_environment = {
        **VALID_PRODUCTION_OVERRIDES,
        variable_name: value,
    }

    assert_settings_invalid(
        monkeypatch,
        expected_message,
        **production_environment,
    )
