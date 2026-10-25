"""Tests for shared frontend templates and static resources."""

from pathlib import Path

import pytest
from django import forms
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string


class SampleForm(forms.Form):
    """Provide a synthetic field for component-rendering tests."""

    identifier = forms.CharField(label="Identifier")


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
