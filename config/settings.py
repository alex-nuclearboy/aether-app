"""Django settings for the Aether project.

Environment-specific and sensitive values are loaded from environment
variables. A local .env file is supported for development, while deployment
environment variables take precedence in production.
"""

import os
import re
from pathlib import Path
from urllib.parse import urlparse

import environ
from django.core.exceptions import ImproperlyConfigured


# ---------------------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

env = environ.Env()

env_file = BASE_DIR / ".env"

if env_file.exists():
    environ.Env.read_env(env_file)


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

DATABASE_ENV_REFERENCE_PATTERN = re.compile(
    r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}"
)


def expand_database_url(database_url: str) -> str:
    """Expand braced environment references in a database URL."""

    def replace_reference(match: re.Match[str]) -> str:
        variable_name = match.group(1)

        try:
            return os.environ[variable_name]
        except KeyError as exc:
            raise ImproperlyConfigured(
                f"DATABASE_URL references undefined environment variable "
                f"{variable_name}."
            ) from exc

    return DATABASE_ENV_REFERENCE_PATTERN.sub(
        replace_reference,
        database_url,
    )


def build_database_config(
    database_url: str,
    conn_max_age: int,
    conn_health_checks: bool,
    connect_timeout: int,
) -> dict[str, object]:
    """Build and validate the Django PostgreSQL configuration."""
    try:
        parsed_url = urlparse(database_url)
        _ = parsed_url.port
    except (TypeError, ValueError) as exc:
        raise ImproperlyConfigured(
            "DATABASE_URL has an invalid format."
        ) from exc

    if not parsed_url.scheme or "://" not in database_url:
        raise ImproperlyConfigured(
            "DATABASE_URL has an invalid format."
        )

    if parsed_url.scheme not in {
        "postgres",
        "postgresql",
        "psql",
        "pgsql",
    }:
        raise ImproperlyConfigured(
            "DATABASE_URL must use PostgreSQL."
        )

    database_config = environ.Env.db_url_config(database_url)

    if database_config.get("ENGINE") != "django.db.backends.postgresql":
        raise ImproperlyConfigured(
            "DATABASE_URL must use PostgreSQL."
        )

    required_values = {
        "NAME": "database name",
        "USER": "database user",
        "PASSWORD": "database password",
        "HOST": "database host",
    }

    missing_values = [
        description
        for key, description in required_values.items()
        if not database_config.get(key)
    ]

    if missing_values:
        missing = ", ".join(missing_values)

        raise ImproperlyConfigured(
            f"DATABASE_URL is missing: {missing}."
        )

    database_config["CONN_MAX_AGE"] = conn_max_age
    database_config["CONN_HEALTH_CHECKS"] = conn_health_checks

    database_options = database_config.get("OPTIONS") or {}

    database_options.setdefault(
        "connect_timeout",
        connect_timeout,
    )

    database_config["OPTIONS"] = database_options

    return database_config


# ---------------------------------------------------------------------------
# Core security settings
# ---------------------------------------------------------------------------

SECRET_KEY = env("DJANGO_SECRET_KEY", default="").strip()

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must not be empty."
    )

DEBUG = env.bool(
    "DJANGO_DEBUG",
    default=False,
)

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=[],
)


# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

DATABASE_URL = env("DATABASE_URL", default="").strip()

if not DATABASE_URL:
    raise ImproperlyConfigured(
        "DATABASE_URL must not be empty."
    )

DATABASE_URL = expand_database_url(DATABASE_URL)

DATABASE_CONN_MAX_AGE = env.int(
    "DATABASE_CONN_MAX_AGE",
    default=0,
)

if DATABASE_CONN_MAX_AGE < 0:
    raise ImproperlyConfigured(
        "DATABASE_CONN_MAX_AGE must not be negative."
    )

DATABASE_CONN_HEALTH_CHECKS = env.bool(
    "DATABASE_CONN_HEALTH_CHECKS",
    default=False,
)

DATABASE_CONNECT_TIMEOUT = env.int(
    "DATABASE_CONNECT_TIMEOUT",
    default=5,
)

if DATABASE_CONNECT_TIMEOUT <= 0:
    raise ImproperlyConfigured(
        "DATABASE_CONNECT_TIMEOUT must be greater than zero."
    )

DATABASES = {
    "default": build_database_config(
        database_url=DATABASE_URL,
        conn_max_age=DATABASE_CONN_MAX_AGE,
        conn_health_checks=DATABASE_CONN_HEALTH_CHECKS,
        connect_timeout=DATABASE_CONNECT_TIMEOUT,
    ),
}


# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = env(
    "DJANGO_LANGUAGE_CODE",
    default="en-gb",
)

TIME_ZONE = env(
    "DJANGO_TIME_ZONE",
    default="UTC",
)

USE_I18N = True
USE_TZ = True


# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = "static/"


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}
