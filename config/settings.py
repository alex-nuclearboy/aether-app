"""Django settings for the Aether project.

Environment-specific and sensitive values are loaded from environment
variables. A local .env file is supported for development, while deployment
environment variables take precedence in production.
"""

from pathlib import Path

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
    "default": env.db_url(
        DATABASE_URL,
    ),
}

DATABASES["default"].update(
    {
        "CONN_MAX_AGE": DATABASE_CONN_MAX_AGE,
        "CONN_HEALTH_CHECKS": DATABASE_CONN_HEALTH_CHECKS,
        "OPTIONS": {
            "connect_timeout": DATABASE_CONNECT_TIMEOUT,
        },
    }
)

if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured(
        "DATABASE_URL must configure a PostgreSQL database."
    )


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
