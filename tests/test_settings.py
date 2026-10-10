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
    "DJANGO_SECRET_KEY": "test-only-secret-key",
    "DJANGO_DEBUG": "True",
    "DJANGO_ALLOWED_HOSTS": "localhost,testserver",
    "DATABASE_URL": VALID_DATABASE_URL,
    "DATABASE_CONN_MAX_AGE": "0",
    "DATABASE_CONN_HEALTH_CHECKS": "False",
    "DATABASE_CONNECT_TIMEOUT": "5",
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
# Module-level settings validation
# ---------------------------------------------------------------------------


def test_settings_load_valid_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load the settings module with a valid development configuration."""
    loaded_settings = _run_settings(monkeypatch)

    assert loaded_settings["SECRET_KEY"] == "test-only-secret-key"
    assert loaded_settings["DEBUG"] is True
    assert loaded_settings["ALLOWED_HOSTS"] == [
        "localhost",
        "testserver",
    ]

    database_config = loaded_settings["DATABASES"]["default"]

    assert database_config["ENGINE"] == "django.db.backends.postgresql"
    assert database_config["NAME"] == "aether"
    assert database_config["CONN_MAX_AGE"] == 0
    assert database_config["CONN_HEALTH_CHECKS"] is False
    assert database_config["OPTIONS"]["connect_timeout"] == 5


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
