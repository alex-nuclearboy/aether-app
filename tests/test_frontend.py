"""Tests for shared frontend templates and static resources."""

from pathlib import Path

import pytest
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.test import override_settings
from django.urls import reverse


class SampleForm(forms.Form):
    """Provide a synthetic field for component-rendering tests."""

    identifier = forms.CharField(label="Identifier")


class DescribedForm(forms.Form):
    """Exercise Django's built-in help/error accessibility attributes."""

    identifier = forms.CharField(
        label="Identifier",
        help_text="Enter a unique identifier.",
    )


def test_form_field_component_renders_label_and_input():
    """Reuse consistent markup for Django form fields."""
    field = SampleForm()["identifier"]
    html = render_to_string(
        "components/form_field.html", {"field": field}
    )

    assert 'class="form-field"' in html
    assert 'for="id_identifier"' in html
    assert 'name="identifier"' in html
    assert "Identifier" in html


def test_form_field_component_renders_validation_errors():
    """Keep field errors with the reusable field markup."""
    form = SampleForm(data={"identifier": ""})
    assert not form.is_valid()
    html = render_to_string(
        "components/form_field.html",
        {"field": form["identifier"]},
    )

    assert 'class="form-field__errors"' in html
    assert "This field is required." in html


def test_form_field_connects_help_text_to_input():
    """Render the help ID expected by Django's aria-describedby."""
    field = DescribedForm()["identifier"]
    html = render_to_string(
        "components/form_field.html", {"field": field}
    )

    assert 'id="id_identifier_helptext"' in html
    assert "Enter a unique identifier." in html
    assert 'aria-describedby="id_identifier_helptext"' in html


def test_form_field_connects_errors_and_help_to_input():
    """Associate both field errors and help text with the widget."""
    form = DescribedForm(data={"identifier": ""})
    assert not form.is_valid()
    html = render_to_string(
        "components/form_field.html",
        {"field": form["identifier"]},
    )

    assert 'id="id_identifier_helptext"' in html
    assert 'id="id_identifier_error"' in html
    assert 'aria-invalid="true"' in html
    assert (
        'aria-describedby="id_identifier_helptext id_identifier_error"'
        in html
    )


@pytest.mark.parametrize(
    "asset",
    [
        "css/foundations/tokens.css",
        "css/layout.css",
        "css/components/button.css",
        "css/components/form-field.css",
    ],
)
def test_shared_stylesheets_are_discoverable(asset):
    """Expose new shared CSS through Django staticfiles."""
    assert finders.find(asset) is not None


def test_responsive_breakpoints_are_declared():
    """Keep the agreed viewport thresholds in the token layer."""
    location = finders.find("css/foundations/tokens.css")
    assert location is not None
    css = Path(location).read_text(encoding="utf-8")

    for breakpoint_width in (640, 1024, 1440):
        assert f"@media (min-width: {breakpoint_width}px)" in css


def test_base_template_loads_shared_styles(client):
    """Load token and component sheets on the public home page."""
    response = client.get("/")

    assert response.status_code == 200
    for asset in (
        b"css/foundations/tokens.css",
        b"css/layout.css",
        b"css/components/button.css",
        b"css/components/form-field.css",
    ):
        assert asset in response.content


@override_settings(REGISTRATION_ENABLED=False)
def test_anonymous_header_links_to_login_and_registration(client):
    """Keep both account routes visible without opening registration."""
    response = client.get(reverse("home"))
    content = response.content.decode()

    assert response.status_code == 200
    assert f'href="{reverse("login")}"' in content
    assert f'href="{reverse("register")}"' in content
    assert "Sign in" in content
    assert "Sign up" in content


@pytest.mark.django_db
def test_authenticated_header_keeps_profile_and_sign_out(client):
    """Do not show anonymous account links after authentication."""
    member = get_user_model().objects.create_user(
        username="header-member",
        email="header-member@example.test",
        password="Synthetic-Passphrase-2026!",
    )
    client.force_login(member)
    response = client.get(reverse("home"))
    content = response.content.decode()

    assert response.status_code == 200
    assert f'href="{reverse("profile")}"' in content
    assert f'action="{reverse("logout")}"' in content
    assert f'href="{reverse("login")}"' not in content
    assert f'href="{reverse("register")}"' not in content
    assert "Sign up" not in content
