"""Tests for the Aether logging configuration."""

from pathlib import Path

import pytest
from django.core.exceptions import ImproperlyConfigured

from config.logging import (
    LOG_COLORS,
    LoggingLevels,
    build_logging_config,
    validate_log_level,
)


def _logging_levels(
    *,
    root: str = "WARNING",
    app: str = "DEBUG",
    django: str = "INFO",
    database: str = "WARNING",
    audit: str = "INFO",
) -> LoggingLevels:
    """Return logging levels suitable for tests."""
    return LoggingLevels(
        root=root,
        app=app,
        django=django,
        database=database,
        audit=audit,
    )


@pytest.mark.parametrize(
    "level",
    [
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ],
)
def test_validate_log_level_accepts_supported_levels(
    level: str,
) -> None:
    """Accept every supported logging level."""
    assert validate_log_level(
        "TEST_LOG_LEVEL",
        level,
    ) == level


def test_validate_log_level_normalises_value() -> None:
    """Strip whitespace and normalise a logging level to uppercase."""
    assert validate_log_level(
        "TEST_LOG_LEVEL",
        "  debug  ",
    ) == "DEBUG"


def test_validate_log_level_rejects_unsupported_level() -> None:
    """Reject an unsupported logging level."""
    with pytest.raises(
        ImproperlyConfigured,
        match=(
            "TEST_LOG_LEVEL must be one of: "
            "CRITICAL, DEBUG, ERROR, INFO, WARNING"
        ),
    ):
        validate_log_level(
            "TEST_LOG_LEVEL",
            "verbose",
        )


def test_development_logging_uses_colour_console(
    tmp_path: Path,
) -> None:
    """Use the coloured console formatter during development."""
    config = build_logging_config(
        base_dir=tmp_path,
        debug=True,
        levels=_logging_levels(),
    )

    assert config["handlers"]["console"]["formatter"] == "colour"
    assert config["formatters"]["colour"]["log_colors"] == LOG_COLORS


def test_production_logging_uses_plain_console(
    tmp_path: Path,
) -> None:
    """Use the plain console formatter in production."""
    config = build_logging_config(
        base_dir=tmp_path,
        debug=False,
        levels=_logging_levels(
            app="WARNING",
            django="WARNING",
        ),
    )

    assert config["handlers"]["console"]["formatter"] == "plain"


def test_development_logging_creates_rotating_file_handler(
    tmp_path: Path,
) -> None:
    """Write development logs to a rotating local log file."""
    config = build_logging_config(
        base_dir=tmp_path,
        debug=True,
        levels=_logging_levels(),
    )

    log_directory = tmp_path / "logs"
    file_handler = config["handlers"]["file"]

    assert log_directory.is_dir()
    assert Path(file_handler["filename"]) == log_directory / "aether.log"
    assert file_handler["class"] == (
        "logging.handlers.RotatingFileHandler"
    )
    assert file_handler["maxBytes"] == 5 * 1024 * 1024
    assert file_handler["backupCount"] == 3
    assert file_handler["encoding"] == "utf-8"
    assert file_handler["formatter"] == "plain"


def test_production_logging_does_not_create_file_handler(
    tmp_path: Path,
) -> None:
    """Avoid writing log files inside the production environment."""
    config = build_logging_config(
        base_dir=tmp_path,
        debug=False,
        levels=_logging_levels(
            app="WARNING",
            django="WARNING",
        ),
    )

    assert "file" not in config["handlers"]
    assert not (tmp_path / "logs").exists()


def test_development_loggers_use_console_and_file(
    tmp_path: Path,
) -> None:
    """Attach configured loggers to console and file in development."""
    config = build_logging_config(
        base_dir=tmp_path,
        debug=True,
        levels=_logging_levels(),
    )

    loggers = config["loggers"]

    assert loggers["aether"]["handlers"] == [
        "console",
        "file",
    ]
    assert loggers["django"]["handlers"] == [
        "console",
        "file",
    ]
    assert loggers["django.db.backends"]["handlers"] == [
        "console",
        "file",
    ]
    assert loggers["aether.audit"]["handlers"] == [
        "console",
        "file",
    ]


def test_production_loggers_use_console_only(
    tmp_path: Path,
) -> None:
    """Attach configured loggers only to console in production."""
    config = build_logging_config(
        base_dir=tmp_path,
        debug=False,
        levels=_logging_levels(
            app="WARNING",
            django="WARNING",
        ),
    )

    loggers = config["loggers"]

    assert loggers["aether"]["handlers"] == ["console"]
    assert loggers["django"]["handlers"] == ["console"]
    assert loggers["django.db.backends"]["handlers"] == ["console"]
    assert loggers["aether.audit"]["handlers"] == ["console"]


def test_logging_levels_are_applied(
    tmp_path: Path,
) -> None:
    """Apply independently configured logging levels."""
    config = build_logging_config(
        base_dir=tmp_path,
        debug=True,
        levels=_logging_levels(
            root="ERROR",
            app="DEBUG",
            django="INFO",
            database="CRITICAL",
            audit="WARNING",
        ),
    )

    assert config["root"]["level"] == "ERROR"
    assert config["loggers"]["aether"]["level"] == "DEBUG"
    assert config["loggers"]["django"]["level"] == "INFO"
    assert (
        config["loggers"]["django.db.backends"]["level"]
        == "CRITICAL"
    )
    assert config["loggers"]["aether.audit"]["level"] == "WARNING"


def test_configured_loggers_do_not_propagate(
    tmp_path: Path,
) -> None:
    """Prevent configured loggers from duplicating messages at root."""
    config = build_logging_config(
        base_dir=tmp_path,
        debug=True,
        levels=_logging_levels(),
    )

    for logger_name in (
        "aether",
        "django",
        "django.db.backends",
        "aether.audit",
    ):
        assert config["loggers"][logger_name]["propagate"] is False


@pytest.mark.parametrize(
    ("field", "environment_name"),
    [
        ("root", "ROOT_LOG_LEVEL"),
        ("app", "APP_LOG_LEVEL"),
        ("django", "DJANGO_LOG_LEVEL"),
        ("database", "DATABASE_LOG_LEVEL"),
        ("audit", "AUDIT_LOG_LEVEL"),
    ],
)
def test_logging_config_rejects_invalid_level(
    tmp_path: Path,
    field: str,
    environment_name: str,
) -> None:
    """Reject invalid values for every configurable logging level."""
    values = {
        "root": "WARNING",
        "app": "DEBUG",
        "django": "INFO",
        "database": "WARNING",
        "audit": "INFO",
    }
    values[field] = "VERBOSE"

    with pytest.raises(
        ImproperlyConfigured,
        match=rf"{environment_name} must be one of:",
    ):
        build_logging_config(
            base_dir=tmp_path,
            debug=True,
            levels=LoggingLevels(
                root=values["root"],
                app=values["app"],
                django=values["django"],
                database=values["database"],
                audit=values["audit"],
            ),
        )


@pytest.mark.parametrize("debug", [True, False])
def test_request_id_filter_covers_every_handler(tmp_path, debug):
    """Provide request IDs to all configured formatters and handlers."""
    config = build_logging_config(
        base_dir=tmp_path, debug=debug, levels=_logging_levels(),
    )
    assert config["filters"]["request_id"]["()"] == (
        "infrastructure.request_id.RequestIdFilter"
    )
    assert all(
        handler["filters"] == ["request_id"]
        for handler in config["handlers"].values()
    )
    assert "{request_id}" in config["formatters"]["plain"]["format"]
    assert "%(request_id)s" in config["formatters"]["colour"]["format"]
