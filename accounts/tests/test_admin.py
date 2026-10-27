"""Tests for Aether accounts administration."""

from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets
from django.test import RequestFactory

from accounts.admin import AetherUserAdmin
from accounts.models import User


def test_user_is_registered_in_admin() -> None:
    """Register the custom user model with Django administration."""
    assert admin.site.is_registered(User)


def test_user_admin_add_form_includes_email() -> None:
    """Expose the required email field when creating users in admin."""
    assert "email" in flatten_fieldsets(AetherUserAdmin.add_fieldsets)


def test_user_admin_requires_email() -> None:
    """Require an email when creating a user in Django admin."""
    request = RequestFactory().get("/admin/accounts/user/add/")

    user_admin = admin.site.get_model_admin(User)
    form_class = user_admin.get_form(request, obj=None)

    assert form_class.base_fields["email"].required is True
