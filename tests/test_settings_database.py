"""PostgreSQL URL parsing and database-configuration settings tests."""

import pytest
from django.core.exceptions import ImproperlyConfigured

from config import settings as project_settings
from tests.settings_helpers import (
    VALID_DATABASE_URL,
    patch_database_parser,
    valid_parsed_database_config,
)


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
    database_config = valid_parsed_database_config()
    database_config["ENGINE"] = "django.db.backends.mysql"

    patch_database_parser(
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
    database_config = valid_parsed_database_config()
    database_config[missing_key] = ""

    patch_database_parser(
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
    database_config = valid_parsed_database_config()
    database_config["OPTIONS"] = {
        "connect_timeout": 30,
        "sslmode": "require",
    }

    patch_database_parser(
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
