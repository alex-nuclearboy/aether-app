"""Logging configuration for the Aether project."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from django.core.exceptions import ImproperlyConfigured


VALID_LOG_LEVELS = {
    "DEBUG",
    "INFO",
    "WARNING",
    "ERROR",
    "CRITICAL",
}

LOG_COLORS = {
    "DEBUG": "cyan",
    "INFO": "green",
    "WARNING": "yellow",
    "ERROR": "red",
    "CRITICAL": "bold_red",
}


def validate_log_level(name: str, value: str) -> str:
    """Normalise and validate a logging level."""
    level = value.strip().upper()

    if level not in VALID_LOG_LEVELS:
        valid_levels = ", ".join(sorted(VALID_LOG_LEVELS))
        raise ImproperlyConfigured(
            f"{name} must be one of: {valid_levels}."
        )

    return level


@dataclass(frozen=True)
class LoggingLevels:
    """Logging levels for the main Aether logger groups."""

    root: str
    app: str
    django: str
    database: str
    audit: str

    def validated(self) -> "LoggingLevels":
        """Return normalised and validated logging levels."""
        return LoggingLevels(
            root=validate_log_level(
                "ROOT_LOG_LEVEL",
                self.root,
            ),
            app=validate_log_level(
                "APP_LOG_LEVEL",
                self.app,
            ),
            django=validate_log_level(
                "DJANGO_LOG_LEVEL",
                self.django,
            ),
            database=validate_log_level(
                "DATABASE_LOG_LEVEL",
                self.database,
            ),
            audit=validate_log_level(
                "AUDIT_LOG_LEVEL",
                self.audit,
            ),
        )


def build_logging_config(
    *,
    base_dir: Path,
    debug: bool,
    levels: LoggingLevels,
) -> dict[str, Any]:
    """Build the Django logging configuration."""
    levels = levels.validated()

    formatters = {
        "plain": {
            "format": (
                "{asctime} {levelname:<8} "
                "{name}: {message}"
            ),
            "style": "{",
        },
        "colour": {
            "()": "colorlog.ColoredFormatter",
            "format": (
                "%(log_color)s%(asctime)s %(levelname)-8s "
                "%(name)s:%(reset)s %(message)s"
            ),
            "log_colors": LOG_COLORS,
        },
    }

    handlers: dict[str, dict[str, Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "colour" if debug else "plain",
        },
    }

    if debug:
        log_directory = base_dir / "logs"
        log_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": log_directory / "aether.log",
            "maxBytes": 5 * 1024 * 1024,
            "backupCount": 3,
            "encoding": "utf-8",
            "formatter": "plain",
        }

    application_handlers = (
        ["console", "file"]
        if debug
        else ["console"]
    )

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": formatters,
        "handlers": handlers,
        "root": {
            "handlers": ["console"],
            "level": levels.root,
        },
        "loggers": {
            "aether": {
                "handlers": application_handlers,
                "level": levels.app,
                "propagate": False,
            },
            "django": {
                "handlers": application_handlers,
                "level": levels.django,
                "propagate": False,
            },
            "django.db.backends": {
                "handlers": application_handlers,
                "level": levels.database,
                "propagate": False,
            },
            "aether.audit": {
                "handlers": application_handlers,
                "level": levels.audit,
                "propagate": False,
            },
        },
    }
