"""Registration feature-gate settings and production restrictions."""

import pytest
from django.core.exceptions import ImproperlyConfigured

from tests.settings_helpers import (
    VALID_PRODUCTION_OVERRIDES,
    run_settings,
)


def test_public_registration_is_disabled_by_default(monkeypatch):
    """Do not allow account creation unless explicitly enabled."""
    settings_dict = run_settings(monkeypatch)
    assert settings_dict["REGISTRATION_ENABLED"] is False


def test_public_registration_can_be_enabled_in_development(monkeypatch):
    """Permit controlled local integration testing of the signup flow."""
    settings_dict = run_settings(
        monkeypatch, AETHER_REGISTRATION_ENABLED="True"
    )
    assert settings_dict["REGISTRATION_ENABLED"] is True


def test_public_registration_is_not_yet_enabled_in_production(monkeypatch):
    """Block production exposure before recovery and abuse controls exist."""
    with pytest.raises(ImproperlyConfigured, match="cannot be enabled"):
        run_settings(
            monkeypatch,
            **VALID_PRODUCTION_OVERRIDES,
            AETHER_REGISTRATION_ENABLED="True",
        )
