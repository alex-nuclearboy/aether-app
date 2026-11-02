"""Registration feature-gate settings and production restrictions."""

from unittest.mock import Mock

import environ
import pytest
from django.core.exceptions import ImproperlyConfigured

from tests.settings_helpers import (
    VALID_PRODUCTION_OVERRIDES,
    run_settings,
)


def test_public_registration_is_disabled_by_default(monkeypatch):
    """Use the actual default when no flag or local env file is loaded."""
    monkeypatch.setattr(environ.Env, "read_env", Mock())
    settings_dict = run_settings(
        monkeypatch, unset=("AETHER_REGISTRATION_ENABLED",)
    )
    assert settings_dict["REGISTRATION_ENABLED"] is False


def test_public_registration_is_disabled_when_explicitly_false(monkeypatch):
    """Ignore a local opt-in when the test environment disables signup."""
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
