"""Tests for Aether accounts administration."""

import pytest
from django.contrib import admin
from django.contrib.admin.utils import flatten_fieldsets
from django.forms import ModelForm
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


def _admin_add_form(email: str) -> ModelForm:
    """Build the standard Django admin add form with a supplied email."""
    request = RequestFactory().get("/admin/accounts/user/add/")
    user_admin = admin.site.get_model_admin(User)
    form_class = user_admin.get_form(request, obj=None)
    return form_class(
        data={
            "username": "test-member",
            "email": email,
            "usable_password": "true",
            "password1": "Secure-Random-Password!7264",
            "password2": "Secure-Random-Password!7264",
        }
    )


@pytest.mark.django_db
@pytest.mark.parametrize("email", ["", "invalid-email", "member@"])
def test_user_admin_add_form_rejects_invalid_email(email: str) -> None:
    """Reject missing or malformed email in the actual admin add form."""
    form = _admin_add_form(email)

    assert not form.is_valid()
    assert "email" in form.errors


@pytest.mark.django_db
def test_user_admin_add_form_accepts_valid_email() -> None:
    """Accept a valid email when other admin form fields are valid."""
    form = _admin_add_form("member@example.com")

    assert form.is_valid(), form.errors.as_json()
