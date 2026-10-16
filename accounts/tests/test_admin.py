"""Tests for Aether accounts administration."""

from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets

from accounts.admin import AetherUserAdmin
from accounts.models import User


def test_user_is_registered_in_admin() -> None:
    """Register the custom user model with Django administration."""
    assert admin.site.is_registered(User)


def test_user_admin_add_form_includes_email() -> None:
    """Expose the required email field when creating users in admin."""
    assert "email" in flatten_fieldsets(AetherUserAdmin.add_fieldsets)
