"""Environment files and core project-settings integration tests."""

from pathlib import Path

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured

from config import settings as project_settings
from tests.settings_helpers import (
    VALID_DATABASE_URL,
    assert_settings_invalid,
    run_settings,
)


def test_settings_reads_local_env_file_when_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load the local environment file when it exists."""
    original_exists = Path.exists
    read_paths: list[Path] = []

    def fake_exists(path: Path) -> bool:
        if path.name == ".env":
            return True
        return original_exists(path)

    def fake_read_env(
        path: object,
        *_args: object,
        **_kwargs: object,
    ) -> None:
        read_paths.append(Path(path))

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(
        environ.Env,
        "read_env",
        staticmethod(fake_read_env),
    )

    run_settings(monkeypatch)

    assert read_paths == [project_settings.BASE_DIR / ".env"]


def test_settings_do_not_read_missing_local_env_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Skip local environment loading when the file does not exist."""
    original_exists = Path.exists

    def fake_exists(path: Path) -> bool:
        if path.name == ".env":
            return False
        return original_exists(path)

    def fail_read_env(
        *_args: object,
        **_kwargs: object,
    ) -> None:
        raise AssertionError("read_env() must not be called.")

    monkeypatch.setattr(Path, "exists", fake_exists)
    monkeypatch.setattr(
        environ.Env,
        "read_env",
        staticmethod(fail_read_env),
    )

    loaded_settings = run_settings(monkeypatch)

    assert loaded_settings["SECRET_KEY"] == "test-only-secret-key"

def test_settings_load_valid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load the settings module with a valid test configuration."""
    loaded_settings = run_settings(monkeypatch)

    assert loaded_settings["ENVIRONMENT"] == "test"
    assert loaded_settings["SECRET_KEY"] == "test-only-secret-key"
    assert loaded_settings["DEBUG"] is True
    assert loaded_settings["ALLOWED_HOSTS"] == [
        "localhost",
        "testserver",
    ]

    assert loaded_settings["CSRF_TRUSTED_ORIGINS"] == []
    assert loaded_settings["SECURE_SSL_REDIRECT"] is False
    assert loaded_settings["SESSION_COOKIE_SECURE"] is False
    assert loaded_settings["CSRF_COOKIE_SECURE"] is False
    assert loaded_settings["SECURE_HSTS_SECONDS"] == 0
    assert loaded_settings["SECURE_HSTS_INCLUDE_SUBDOMAINS"] is False
    assert loaded_settings["SECURE_HSTS_PRELOAD"] is False

    database_config = loaded_settings["DATABASES"]["default"]

    assert database_config["ENGINE"] == "django.db.backends.postgresql"
    assert database_config["NAME"] == "aether"
    assert database_config["CONN_MAX_AGE"] == 0
    assert database_config["CONN_HEALTH_CHECKS"] is False
    assert database_config["OPTIONS"]["connect_timeout"] == 5


def test_settings_apply_logging_level_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Apply logging levels supplied through environment variables."""
    loaded_settings = run_settings(
        monkeypatch,
        ROOT_LOG_LEVEL="ERROR",
        APP_LOG_LEVEL="INFO",
        DJANGO_LOG_LEVEL="ERROR",
        DATABASE_LOG_LEVEL="CRITICAL",
        AUDIT_LOG_LEVEL="WARNING",
    )

    logging_config = loaded_settings["LOGGING"]

    assert logging_config["root"]["level"] == "ERROR"
    assert logging_config["loggers"]["aether"]["level"] == "INFO"
    assert logging_config["loggers"]["django"]["level"] == "ERROR"
    assert (
        logging_config["loggers"]["django.db.backends"]["level"]
        == "CRITICAL"
    )
    assert (
        logging_config["loggers"]["aether.audit"]["level"]
        == "WARNING"
    )


def test_settings_reject_empty_secret_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject an empty Django secret key."""
    with pytest.raises(
        ImproperlyConfigured,
        match="DJANGO_SECRET_KEY must not be empty",
    ):
        run_settings(
            monkeypatch,
            DJANGO_SECRET_KEY="",
        )


def test_settings_reject_empty_database_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject an empty PostgreSQL connection URL."""
    with pytest.raises(
        ImproperlyConfigured,
        match="DATABASE_URL must not be empty",
    ):
        run_settings(
            monkeypatch,
            DATABASE_URL="",
        )


def test_settings_expand_database_url_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expand database environment references during settings loading."""
    monkeypatch.setenv("TEST_DATABASE_USER", "aether")

    loaded_settings = run_settings(
        monkeypatch,
        DATABASE_URL=(
            "postgresql://${TEST_DATABASE_USER}:"
            "test-password@127.0.0.1:5432/aether"
        ),
    )

    assert loaded_settings["DATABASE_URL"] == VALID_DATABASE_URL


def test_settings_reject_undefined_database_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject unresolved references while loading settings."""
    monkeypatch.delenv(
        "UNDEFINED_DATABASE_USER",
        raising=False,
    )

    assert_settings_invalid(
        monkeypatch,
        (
            "DATABASE_URL references undefined environment variable "
            "UNDEFINED_DATABASE_USER"
        ),
        DATABASE_URL=(
            "postgresql://${UNDEFINED_DATABASE_USER}:"
            "test-password@127.0.0.1:5432/aether"
        ),
    )


def test_settings_reject_negative_connection_lifetime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a negative persistent-connection lifetime."""
    with pytest.raises(
        ImproperlyConfigured,
        match="DATABASE_CONN_MAX_AGE must not be negative",
    ):
        run_settings(
            monkeypatch,
            DATABASE_CONN_MAX_AGE="-1",
        )


@pytest.mark.parametrize(
    "connect_timeout",
    [
        "0",
        "-1",
    ],
)
def test_settings_reject_non_positive_connect_timeout(
    monkeypatch: pytest.MonkeyPatch,
    connect_timeout: str,
) -> None:
    """Reject zero and negative database connection timeouts."""
    with pytest.raises(
        ImproperlyConfigured,
        match=(
            "DATABASE_CONNECT_TIMEOUT must be greater than zero"
        ),
    ):
        run_settings(
            monkeypatch,
            DATABASE_CONNECT_TIMEOUT=connect_timeout,
        )
