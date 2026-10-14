"""Tests for the Aether project settings."""

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


def _run_settings(
    monkeypatch: pytest.MonkeyPatch,
    **overrides: str,
) -> dict[str, object]:
    """Execute the settings module with a controlled environment."""
    environment = {
        **VALID_ENVIRONMENT,
        **overrides,
    }

    for name, value in environment.items():
        monkeypatch.setenv(name, value)

    return runpy.run_path(
        str(SETTINGS_PATH),
        run_name="aether_test_settings",
    )


def _valid_parsed_database_config() -> dict[str, object]:
    """Return a valid parsed PostgreSQL database configuration."""
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "aether",
        "USER": "aether",
        "PASSWORD": "test-password",
        "HOST": "127.0.0.1",
        "PORT": 5432,
    }


def _patch_database_parser(
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


# ---------------------------------------------------------------------------
# Environment file handling
# ---------------------------------------------------------------------------


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

    _run_settings(monkeypatch)

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

    loaded_settings = _run_settings(monkeypatch)

    assert loaded_settings["SECRET_KEY"] == "test-only-secret-key"


# ---------------------------------------------------------------------------
# Database URL expansion
# ---------------------------------------------------------------------------


def test_expand_database_url_without_references() -> None:
    """Leave a database URL without environment references unchanged."""
    assert (
        project_settings.expand_database_url(VALID_DATABASE_URL)
        == VALID_DATABASE_URL
    )


def test_expand_database_url_expands_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expand a braced environment reference in a database URL."""
    monkeypatch.setenv("TEST_DATABASE_USER", "aether")

    database_url = (
        "postgresql://${TEST_DATABASE_USER}:"
        "test-password@127.0.0.1:5432/aether"
    )

    assert project_settings.expand_database_url(database_url) == (
        VALID_DATABASE_URL
    )


def test_expand_database_url_expands_multiple_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expand multiple environment references in a database URL."""
    monkeypatch.setenv("TEST_DATABASE_USER", "aether")
    monkeypatch.setenv("TEST_DATABASE_PASSWORD", "test-password")

    database_url = (
        "postgresql://${TEST_DATABASE_USER}:"
        "${TEST_DATABASE_PASSWORD}@127.0.0.1:5432/aether"
    )

    assert project_settings.expand_database_url(database_url) == (
        VALID_DATABASE_URL
    )


def test_expand_database_url_rejects_undefined_reference(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a database URL containing an undefined reference."""
    monkeypatch.delenv(
        "TEST_DATABASE_USER",
        raising=False,
    )

    with pytest.raises(
        ImproperlyConfigured,
        match=(
            "DATABASE_URL references undefined environment variable "
            "TEST_DATABASE_USER"
        ),
    ):
        project_settings.expand_database_url(
            "postgresql://${TEST_DATABASE_USER}:"
            "test-password@127.0.0.1:5432/aether"
        )


# ---------------------------------------------------------------------------
# Database configuration
# ---------------------------------------------------------------------------


def test_build_database_config_returns_postgresql_settings() -> None:
    """Build Django database settings from a valid PostgreSQL URL."""
    database_config = project_settings.build_database_config(
        database_url=VALID_DATABASE_URL,
        conn_max_age=0,
        conn_health_checks=False,
        connect_timeout=5,
    )

    assert database_config["ENGINE"] == "django.db.backends.postgresql"
    assert database_config["NAME"] == "aether"
    assert database_config["USER"] == "aether"
    assert database_config["PASSWORD"] == "test-password"
    assert database_config["HOST"] == "127.0.0.1"
    assert str(database_config["PORT"]) == "5432"
    assert database_config["CONN_MAX_AGE"] == 0
    assert database_config["CONN_HEALTH_CHECKS"] is False
    assert database_config["OPTIONS"]["connect_timeout"] == 5


@pytest.mark.parametrize(
    "database_url",
    [
        "aether:test-password@127.0.0.1:5432/aether",
        "postgresql://aether:test-password@127.0.0.1:not-a-port/aether",
    ],
)
def test_build_database_config_rejects_invalid_format(
    database_url: str,
) -> None:
    """Reject malformed PostgreSQL database URLs."""
    with pytest.raises(
        ImproperlyConfigured,
        match="DATABASE_URL has an invalid format",
    ):
        project_settings.build_database_config(
            database_url=database_url,
            conn_max_age=0,
            conn_health_checks=False,
            connect_timeout=5,
        )


@pytest.mark.parametrize(
    "database_url",
    [
        "sqlite:///database.sqlite3",
        "mysql://aether:test-password@127.0.0.1:3306/aether",
    ],
)
def test_build_database_config_rejects_non_postgresql_scheme(
    database_url: str,
) -> None:
    """Reject database backends other than PostgreSQL."""
    with pytest.raises(
        ImproperlyConfigured,
        match="DATABASE_URL must use PostgreSQL",
    ):
        project_settings.build_database_config(
            database_url=database_url,
            conn_max_age=0,
            conn_health_checks=False,
            connect_timeout=5,
        )


def test_build_database_config_rejects_unexpected_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a parsed configuration that does not use PostgreSQL."""
    database_config = _valid_parsed_database_config()
    database_config["ENGINE"] = "django.db.backends.mysql"

    _patch_database_parser(
        monkeypatch,
        database_config,
    )

    with pytest.raises(
        ImproperlyConfigured,
        match="DATABASE_URL must use PostgreSQL",
    ):
        project_settings.build_database_config(
            database_url=VALID_DATABASE_URL,
            conn_max_age=0,
            conn_health_checks=False,
            connect_timeout=5,
        )


@pytest.mark.parametrize(
    ("missing_key", "description"),
    [
        ("NAME", "database name"),
        ("USER", "database user"),
        ("PASSWORD", "database password"),
        ("HOST", "database host"),
    ],
)
def test_build_database_config_requires_connection_value(
    monkeypatch: pytest.MonkeyPatch,
    missing_key: str,
    description: str,
) -> None:
    """Reject PostgreSQL configurations missing required values."""
    database_config = _valid_parsed_database_config()
    database_config[missing_key] = ""

    _patch_database_parser(
        monkeypatch,
        database_config,
    )

    with pytest.raises(
        ImproperlyConfigured,
        match=rf"DATABASE_URL is missing: {description}\.",
    ):
        project_settings.build_database_config(
            database_url=VALID_DATABASE_URL,
            conn_max_age=0,
            conn_health_checks=False,
            connect_timeout=5,
        )


def test_build_database_config_applies_connection_settings() -> None:
    """Apply configured persistent-connection behaviour."""
    database_config = project_settings.build_database_config(
        database_url=VALID_DATABASE_URL,
        conn_max_age=60,
        conn_health_checks=True,
        connect_timeout=10,
    )

    assert database_config["CONN_MAX_AGE"] == 60
    assert database_config["CONN_HEALTH_CHECKS"] is True
    assert database_config["OPTIONS"]["connect_timeout"] == 10


def test_build_database_config_preserves_existing_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preserve database options already supplied by the parser."""
    database_config = _valid_parsed_database_config()
    database_config["OPTIONS"] = {
        "connect_timeout": 30,
        "sslmode": "require",
    }

    _patch_database_parser(
        monkeypatch,
        database_config,
    )

    result = project_settings.build_database_config(
        database_url=VALID_DATABASE_URL,
        conn_max_age=0,
        conn_health_checks=False,
        connect_timeout=5,
    )

    assert result["OPTIONS"]["connect_timeout"] == 30
    assert result["OPTIONS"]["sslmode"] == "require"


# ---------------------------------------------------------------------------
# Security configuration
# ---------------------------------------------------------------------------


def test_settings_normalise_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normalise the configured runtime environment."""
    loaded_settings = _run_settings(
        monkeypatch,
        AETHER_ENVIRONMENT="  DeVeLoPmEnT  ",
    )

    assert loaded_settings["ENVIRONMENT"] == "development"


@pytest.mark.parametrize(
    "environment",
    [
        "",
        "staging",
    ],
)
def test_settings_reject_invalid_environment(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
) -> None:
    """Reject empty and unsupported runtime environments."""
    with pytest.raises(
        ImproperlyConfigured,
        match="AETHER_ENVIRONMENT must be one of:",
    ):
        _run_settings(
            monkeypatch,
            AETHER_ENVIRONMENT=environment,
        )


def test_settings_load_valid_production_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load settings with the required production safeguards."""
    loaded_settings = _run_settings(
        monkeypatch,
        **VALID_PRODUCTION_OVERRIDES,
    )

    assert loaded_settings["ENVIRONMENT"] == "production"
    assert loaded_settings["DEBUG"] is False
    assert loaded_settings["ALLOWED_HOSTS"] == ["aether.example"]
    assert loaded_settings["SESSION_COOKIE_SECURE"] is True
    assert loaded_settings["CSRF_COOKIE_SECURE"] is True


def test_settings_reject_debug_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject Django debug mode in production."""
    production_environment = {
        **VALID_PRODUCTION_OVERRIDES,
        "DJANGO_DEBUG": "True",
    }

    with pytest.raises(
        ImproperlyConfigured,
        match="DJANGO_DEBUG must be False in production",
    ):
        _run_settings(
            monkeypatch,
            **production_environment,
        )


def test_settings_require_allowed_hosts_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require at least one allowed host in production."""
    production_environment = {
        **VALID_PRODUCTION_OVERRIDES,
        "DJANGO_ALLOWED_HOSTS": "",
    }

    with pytest.raises(
        ImproperlyConfigured,
        match="DJANGO_ALLOWED_HOSTS must be configured in production",
    ):
        _run_settings(
            monkeypatch,
            **production_environment,
        )


def test_settings_reject_wildcard_host_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject an unrestricted allowed-host wildcard in production."""
    production_environment = {
        **VALID_PRODUCTION_OVERRIDES,
        "DJANGO_ALLOWED_HOSTS": "aether.example,*",
    }

    with pytest.raises(
        ImproperlyConfigured,
        match="DJANGO_ALLOWED_HOSTS must not contain",
    ):
        _run_settings(
            monkeypatch,
            **production_environment,
        )


def test_settings_require_secure_session_cookie_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require secure session cookies in production."""
    production_environment = {
        **VALID_PRODUCTION_OVERRIDES,
        "DJANGO_SESSION_COOKIE_SECURE": "False",
    }

    with pytest.raises(
        ImproperlyConfigured,
        match=(
            "DJANGO_SESSION_COOKIE_SECURE must be True "
            "in production"
        ),
    ):
        _run_settings(
            monkeypatch,
            **production_environment,
        )


def test_settings_require_secure_csrf_cookie_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Require secure CSRF cookies in production."""
    production_environment = {
        **VALID_PRODUCTION_OVERRIDES,
        "DJANGO_CSRF_COOKIE_SECURE": "False",
    }

    with pytest.raises(
        ImproperlyConfigured,
        match=(
            "DJANGO_CSRF_COOKIE_SECURE must be True "
            "in production"
        ),
    ):
        _run_settings(
            monkeypatch,
            **production_environment,
        )


def test_settings_normalise_csrf_trusted_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normalise configured CSRF trusted origins."""
    loaded_settings = _run_settings(
        monkeypatch,
        DJANGO_CSRF_TRUSTED_ORIGINS=(
            " https://aether.example/, "
            "https://api.aether.example/ "
        ),
    )

    assert loaded_settings["CSRF_TRUSTED_ORIGINS"] == [
        "https://aether.example",
        "https://api.aether.example",
    ]


def test_settings_apply_security_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Apply environment-controlled Django security settings."""
    loaded_settings = _run_settings(
        monkeypatch,
        DJANGO_SECURE_SSL_REDIRECT="True",
        DJANGO_SESSION_COOKIE_SECURE="True",
        DJANGO_CSRF_COOKIE_SECURE="True",
        DJANGO_SECURE_HSTS_SECONDS="300",
        DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS="True",
        DJANGO_SECURE_HSTS_PRELOAD="True",
    )

    assert loaded_settings["SECURE_SSL_REDIRECT"] is True
    assert loaded_settings["SESSION_COOKIE_SECURE"] is True
    assert loaded_settings["CSRF_COOKIE_SECURE"] is True
    assert loaded_settings["SECURE_HSTS_SECONDS"] == 300
    assert loaded_settings["SECURE_HSTS_INCLUDE_SUBDOMAINS"] is True
    assert loaded_settings["SECURE_HSTS_PRELOAD"] is True


def test_settings_reject_negative_hsts_seconds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Reject a negative HSTS duration."""
    with pytest.raises(
        ImproperlyConfigured,
        match="DJANGO_SECURE_HSTS_SECONDS must not be negative",
    ):
        _run_settings(
            monkeypatch,
            DJANGO_SECURE_HSTS_SECONDS="-1",
        )


# ---------------------------------------------------------------------------
# Email configuration
# ---------------------------------------------------------------------------


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
    loaded_settings = _run_settings(
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
    loaded_settings = _run_settings(
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

    loaded_settings = _run_settings(
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

    with pytest.raises(
        ImproperlyConfigured,
        match=expected_message,
    ):
        _run_settings(
            monkeypatch,
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

    with pytest.raises(
        ImproperlyConfigured,
        match="MAILER_SMTP_PASSWORD must not be empty in production",
    ):
        _run_settings(
            monkeypatch,
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

    with pytest.raises(
        ImproperlyConfigured,
        match=expected_message,
    ):
        _run_settings(
            monkeypatch,
            **production_environment,
        )


# ---------------------------------------------------------------------------
# Module-level settings validation
# ---------------------------------------------------------------------------


def test_settings_load_valid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load the settings module with a valid test configuration."""
    loaded_settings = _run_settings(monkeypatch)

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
    loaded_settings = _run_settings(
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
        _run_settings(
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
        _run_settings(
            monkeypatch,
            DATABASE_URL="",
        )


def test_settings_expand_database_url_references(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Expand database environment references during settings loading."""
    monkeypatch.setenv("TEST_DATABASE_USER", "aether")

    loaded_settings = _run_settings(
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

    with pytest.raises(
        ImproperlyConfigured,
        match=(
            "DATABASE_URL references undefined environment variable "
            "UNDEFINED_DATABASE_USER"
        ),
    ):
        _run_settings(
            monkeypatch,
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
        _run_settings(
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
        _run_settings(
            monkeypatch,
            DATABASE_CONNECT_TIMEOUT=connect_timeout,
        )
