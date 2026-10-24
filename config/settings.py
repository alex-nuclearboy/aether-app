"""Django settings for the Aether project.

Environment-specific and sensitive values are loaded from environment
variables. A local .env file is supported for development, while deployment
environment variables take precedence in production.
"""

import os
import re
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

import environ
from django.core.exceptions import ImproperlyConfigured

from config.logging import LoggingLevels, build_logging_config


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

ENVIRONMENT = env(
    "AETHER_ENVIRONMENT",
    default="",
).strip().lower()

SUPPORTED_ENVIRONMENTS = {
    "development",
    "test",
    "production",
}

if ENVIRONMENT not in SUPPORTED_ENVIRONMENTS:
    raise ImproperlyConfigured(
        "AETHER_ENVIRONMENT must be one of: "
        f"{', '.join(sorted(SUPPORTED_ENVIRONMENTS))}."
    )

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="",
).strip()

if not SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must not be empty."
    )


DEBUG = env.bool(
    "DJANGO_DEBUG",
    default=False,
)

if ENVIRONMENT == "production" and DEBUG:
    raise ImproperlyConfigured(
        "DJANGO_DEBUG must be False in production."
    )


ALLOWED_HOSTS = [
    host.strip()
    for host in env.list(
        "DJANGO_ALLOWED_HOSTS",
        default=[],
    )
    if host.strip()
]

if ENVIRONMENT == "production" and not ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must be configured in production."
    )

if ENVIRONMENT == "production" and "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured(
        "DJANGO_ALLOWED_HOSTS must not contain '*' in production."
    )


CSRF_TRUSTED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in env.list(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        default=[],
    )
    if origin.strip()
]


SECURE_SSL_REDIRECT = env.bool(
    "DJANGO_SECURE_SSL_REDIRECT",
    default=False,
)


SESSION_COOKIE_SECURE = env.bool(
    "DJANGO_SESSION_COOKIE_SECURE",
    default=False,
)

if ENVIRONMENT == "production" and not SESSION_COOKIE_SECURE:
    raise ImproperlyConfigured(
        "DJANGO_SESSION_COOKIE_SECURE must be True in production."
    )


CSRF_COOKIE_SECURE = env.bool(
    "DJANGO_CSRF_COOKIE_SECURE",
    default=False,
)

if ENVIRONMENT == "production" and not CSRF_COOKIE_SECURE:
    raise ImproperlyConfigured(
        "DJANGO_CSRF_COOKIE_SECURE must be True in production."
    )


SECURE_HSTS_SECONDS = env.int(
    "DJANGO_SECURE_HSTS_SECONDS",
    default=0,
)

if SECURE_HSTS_SECONDS < 0:
    raise ImproperlyConfigured(
        "DJANGO_SECURE_HSTS_SECONDS must not be negative."
    )


SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS",
    default=False,
)

SECURE_HSTS_PRELOAD = env.bool(
    "DJANGO_SECURE_HSTS_PRELOAD",
    default=False,
)


# ---------------------------------------------------------------------------
# Client IP resolution
# ---------------------------------------------------------------------------

CLIENT_IP_META_PRECEDENCE_ORDER = (
    ("HTTP_X_FORWARDED_FOR", "REMOTE_ADDR")
    if ENVIRONMENT == "production"
    else ("REMOTE_ADDR",)
)

# Development and tests use REMOTE_ADDR only.
# Production uses the last X-Forwarded-For address appended by Koyeb.
# The production branch in infrastructure.request handles this explicitly.
CLIENT_IP_PROXY_ORDER = "right-most"
CLIENT_IP_PROXY_COUNT = None
CLIENT_IP_PROXY_TRUSTED_IPS = None


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
    "axes",
    "accounts.apps.AccountsConfig",
    "core.apps.CoreConfig",
]

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "accounts.backends.AsyncAxesStandaloneBackend",
    "accounts.backends.UsernameOrEmailBackend",
]

MIDDLEWARE = [
    "infrastructure.request_id.request_id_middleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "axes.middleware.AxesMiddleware",
]


# ---------------------------------------------------------------------------
# Authentication lockout protection
# ---------------------------------------------------------------------------

AXES_ENABLED = True

AXES_HANDLER = "axes.handlers.database.AxesDatabaseHandler"

AXES_FAILURE_LIMIT = 3
AXES_COOLOFF_TIME = timedelta(minutes=15)

AXES_LOCK_OUT_AT_FAILURE = True
AXES_LOCKOUT_PARAMETERS = [
    ["username", "ip_address"],
]

AXES_USERNAME_CALLABLE = "accounts.lockouts.get_lockout_username"
AXES_CLIENT_IP_CALLABLE = "infrastructure.request.get_client_ip"

AXES_RESET_ON_SUCCESS = True
AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False

AXES_ONLY_ADMIN_SITE = False
AXES_HTTP_RESPONSE_CODE = 429
AXES_LOCKOUT_CALLABLE = "accounts.lockout_responses.lockout_response"


ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

LOGGING = build_logging_config(
    base_dir=BASE_DIR,
    debug=DEBUG,
    levels=LoggingLevels(
        root=env(
            "ROOT_LOG_LEVEL",
            default="WARNING",
        ),
        app=env(
            "APP_LOG_LEVEL",
            default="DEBUG" if DEBUG else "WARNING",
        ),
        django=env(
            "DJANGO_LOG_LEVEL",
            default="INFO" if DEBUG else "WARNING",
        ),
        database=env(
            "DATABASE_LOG_LEVEL",
            default="WARNING",
        ),
        audit=env(
            "AUDIT_LOG_LEVEL",
            default="INFO",
        ),
    ),
)


# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------

DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL",
    default="",
).strip()

if ENVIRONMENT == "production":
    MAILER_SMTP_HOST = env(
        "MAILER_SMTP_HOST",
        default="",
    ).strip()

    MAILER_SMTP_PORT = env.int(
        "MAILER_SMTP_PORT",
        default=587,
    )

    MAILER_SMTP_USERNAME = env(
        "MAILER_SMTP_USERNAME",
        default="",
    ).strip()

    MAILER_SMTP_PASSWORD = env(
        "MAILER_SMTP_PASSWORD",
        default="",
    )

    MAILER_SMTP_TIMEOUT = env.int(
        "MAILER_SMTP_TIMEOUT",
        default=10,
    )

    if not MAILER_SMTP_HOST:
        raise ImproperlyConfigured(
            "MAILER_SMTP_HOST must not be empty in production."
        )

    if MAILER_SMTP_PORT <= 0:
        raise ImproperlyConfigured(
            "MAILER_SMTP_PORT must be greater than zero."
        )

    if not MAILER_SMTP_USERNAME:
        raise ImproperlyConfigured(
            "MAILER_SMTP_USERNAME must not be empty in production."
        )

    if not MAILER_SMTP_PASSWORD.strip():
        raise ImproperlyConfigured(
            "MAILER_SMTP_PASSWORD must not be empty in production."
        )

    if MAILER_SMTP_TIMEOUT <= 0:
        raise ImproperlyConfigured(
            "MAILER_SMTP_TIMEOUT must be greater than zero."
        )

    if not DEFAULT_FROM_EMAIL:
        raise ImproperlyConfigured(
            "DJANGO_DEFAULT_FROM_EMAIL must not be empty in production."
        )

    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
            "OPTIONS": {
                "host": MAILER_SMTP_HOST,
                "port": MAILER_SMTP_PORT,
                "username": MAILER_SMTP_USERNAME,
                "password": MAILER_SMTP_PASSWORD,
                "use_tls": True,
                "timeout": MAILER_SMTP_TIMEOUT,
            },
        },
    }
else:
    MAILERS = {
        "default": {
            "BACKEND": "django.core.mail.backends.console.EmailBackend",
        },
    }
