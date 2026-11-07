"""Production security and client-IP settings validation tests."""

import pytest
from django.core.exceptions import ImproperlyConfigured

from tests.settings_helpers import (
    VALID_PRODUCTION_OVERRIDES,
    run_settings,
)


def test_settings_normalise_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normalise the configured runtime environment."""
    loaded_settings = run_settings(
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
        run_settings(
            monkeypatch,
            AETHER_ENVIRONMENT=environment,
        )


def test_settings_load_valid_production_configuration(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Load settings with the required production safeguards."""
    loaded_settings = run_settings(
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
        run_settings(
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
        run_settings(
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
        run_settings(
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
        run_settings(
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
        run_settings(
            monkeypatch,
            **production_environment,
        )


def test_settings_normalise_csrf_trusted_origins(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normalise configured CSRF trusted origins."""
    loaded_settings = run_settings(
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
    loaded_settings = run_settings(
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
        run_settings(
            monkeypatch,
            DJANGO_SECURE_HSTS_SECONDS="-1",
        )

@pytest.mark.parametrize(
    ("environment", "expected_headers", "expected_order"),
    [
        ("development", ("REMOTE_ADDR",), "right-most"),
        ("test", ("REMOTE_ADDR",), "right-most"),
        ("production", ("HTTP_X_FORWARDED_FOR",), "right-most"),
    ],
)
def test_client_ip_configuration_by_environment(
    monkeypatch: pytest.MonkeyPatch,
    environment: str,
    expected_headers: tuple[str, ...],
    expected_order: str,
) -> None:
    """Configure client IP resolution for each runtime environment."""
    overrides = {"AETHER_ENVIRONMENT": environment}
    if environment == "production":
        overrides.update(VALID_PRODUCTION_OVERRIDES)

    configured = run_settings(monkeypatch, **overrides)

    assert configured["CLIENT_IP_META_PRECEDENCE_ORDER"] == expected_headers
    assert configured["CLIENT_IP_PROXY_ORDER"] == expected_order
    assert configured["CLIENT_IP_PROXY_COUNT"] is None
    assert configured["CLIENT_IP_PROXY_TRUSTED_IPS"] is None
