"""Tests for Aether's core pages."""

from django.contrib.staticfiles import finders
from django.urls import resolve, reverse


def test_home_url_is_registered():
    """Expose the home page at the root URL."""
    url = reverse("home")
    match = resolve(url)

    assert url == "/"
    assert match.url_name == "home"


def test_home_page_is_accessible(client):
    """Allow anonymous visitors to access the home page."""
    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert b"<h1>Aether</h1>" in response.content


def test_home_page_uses_shared_template(client):
    """Render the home page through the shared base layout."""
    response = client.get(reverse("home"))

    template_names = [
        template.name
        for template in response.templates
    ]

    assert "core/home.html" in template_names
    assert "base.html" in template_names


def test_base_stylesheet_is_discoverable():
    """Expose the base stylesheet through Django staticfiles."""
    assert finders.find("css/base.css") is not None
