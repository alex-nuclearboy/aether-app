"""Reusable helpers for isolated Aether settings configuration tests."""

import runpy
from pathlib import Path

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured

from config import settings as project_settings


SETTINGS_PATH = Path(project_settings.__file__).resolve()

VALID_DATABASE_URL = (
    "postgresql://aether:test-password@127.0.0.1:5432/aether"
)

VALID_ENVIRONMENT = {
    "AETHER_ENVIRONMENT": "test",
    "DJANGO_SECRET_KEY": "test-only-secret-key",
    "DJANGO_DEBUG": "True",
    "DJANGO_ALLOWED_HOSTS": "localhost,testserver",
    "DJANGO_CSRF_TRUSTED_ORIGINS": "",
    "DJANGO_SECURE_SSL_REDIRECT": "False",
    "DJANGO_SESSION_COOKIE_SECURE": "False",
    "DJANGO_CSRF_COOKIE_SECURE": "False",
    "DJANGO_SECURE_HSTS_SECONDS": "0",
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS": "False",
    "DJANGO_SECURE_HSTS_PRELOAD": "False",
    "DATABASE_URL": VALID_DATABASE_URL,
    "DATABASE_CONN_MAX_AGE": "0",
    "DATABASE_CONN_HEALTH_CHECKS": "False",
    "DATABASE_CONNECT_TIMEOUT": "5",
    "DJANGO_DEFAULT_FROM_EMAIL": "test@example.com",
    "AETHER_REGISTRATION_ENABLED": "False",
}

VALID_PRODUCTION_OVERRIDES = {
    "AETHER_ENVIRONMENT": "production",
    "DJANGO_DEBUG": "False",
    "DJANGO_ALLOWED_HOSTS": "aether.example",
    "DJANGO_SESSION_COOKIE_SECURE": "True",
    "DJANGO_CSRF_COOKIE_SECURE": "True",
    "DJANGO_DEFAULT_FROM_EMAIL": "aether@example.com",
    "MAILER_SMTP_HOST": "smtp.example.com",
    "MAILER_SMTP_USERNAME": "test-smtp-user",
    "MAILER_SMTP_PASSWORD": "test-smtp-password",
}


def run_settings(
    monkeypatch: pytest.MonkeyPatch,
    *,
    unset: tuple[str, ...] = (),
    **overrides: str,
) -> dict[str, object]:
    """Execute the settings module with a controlled environment."""
    environment = {
        **VALID_ENVIRONMENT,
        **overrides,
    }

    for name in unset:
        environment.pop(name, None)
        monkeypatch.delenv(name, raising=False)

    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    return runpy.run_path(
        str(SETTINGS_PATH),
        run_name="aether_test_settings",
    )


def assert_settings_invalid(
    monkeypatch: pytest.MonkeyPatch,
    expected_message: str,
    **overrides: str,
) -> None:
    """Check that settings loading rejects the supplied configuration."""
    with pytest.raises(ImproperlyConfigured, match=expected_message):
        run_settings(monkeypatch, **overrides)


def valid_parsed_database_config() -> dict[str, object]:
    """Return a valid parsed PostgreSQL database configuration."""
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "aether",
        "USER": "aether",
        "PASSWORD": "test-password",
        "HOST": "127.0.0.1",
        "PORT": 5432,
    }


def patch_database_parser(
    monkeypatch: pytest.MonkeyPatch,
    database_config: dict[str, object],
) -> None:
    """Replace django-environ database parsing with a controlled result."""

    def fake_db_url_config(_database_url: str) -> dict[str, object]:
        return database_config.copy()

    monkeypatch.setattr(
        environ.Env,
        "db_url_config",
        staticmethod(fake_db_url_config),
    )
