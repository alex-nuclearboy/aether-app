"""Check the supported languages and standard Django localisation wiring."""

import pytest
from django.conf import settings
from django.urls import reverse

from tests.settings_helpers import run_settings


def test_multilingual_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use English (UK) as the default and three explicit locales."""
    loaded = run_settings(monkeypatch, DJANGO_LANGUAGE_CODE="en-gb")

    assert loaded["LANGUAGE_CODE"] == "en-gb"
    assert loaded["LANGUAGES"] == [
        ("en-gb", "English (UK)"),
        ("uk", "Українська"),
        ("pl", "Polski"),
    ]
    assert loaded["LOCALE_PATHS"] == [settings.BASE_DIR / "locale"]
    assert (settings.BASE_DIR / "locale").is_dir()
    assert loaded["USE_I18N"] is True


def test_locale_middleware_order(monkeypatch: pytest.MonkeyPatch) -> None:
    """Resolve language after sessions and before CommonMiddleware."""
    middleware = run_settings(monkeypatch)["MIDDLEWARE"]

    assert middleware.index(
        "django.contrib.sessions.middleware.SessionMiddleware"
    ) < middleware.index("django.middleware.locale.LocaleMiddleware")
    assert middleware.index(
        "django.middleware.locale.LocaleMiddleware"
    ) < middleware.index("django.middleware.common.CommonMiddleware")


def test_language_post_endpoint_is_available() -> None:
    """Keep language changes on Django's built-in POST endpoint."""
    assert reverse("set_language") == "/i18n/setlang/"
    assert reverse("email_verification_confirm", args=["a", "b"]) == (
        "/email/verify/a/b/"
    )
    assert reverse("password_reset_confirm", args=["a", "b"]) == (
        "/password/reset/confirm/a/b/"
    )
