"""Application configuration for Aether accounts."""

from importlib import import_module

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration for the accounts application."""

    name = "accounts"

    def ready(self) -> None:
        """Register authentication audit signal receivers."""
        import_module("accounts.audit")
