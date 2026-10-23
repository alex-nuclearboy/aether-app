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
    assert b'<h1 class="home__title">' in response.content
    assert b'alt="Aether"' in response.content


def test_home_page_uses_shared_template(client):
    """Render the home page through the shared base layout."""
    response = client.get(reverse("home"))

    template_names = [
        template.name
        for template in response.templates
    ]

    assert "core/home.html" in template_names
    assert "base.html" in template_names


def test_home_logo_is_discoverable():
    """Find the full home page logo through Django staticfiles."""
    assert finders.find("images/aether_logo_full.png") is not None


def test_home_stylesheet_is_discoverable():
    """Expose the home page stylesheet through Django staticfiles."""
    assert finders.find("css/pages/home.css") is not None


def test_header_contains_home_link(client):
    """Display a clickable brand linking to the home page."""
    response = client.get(reverse("home"))

    assert b'<a class="site-brand" href="/">' in response.content
    assert b'<span class="site-brand__name">Aether</span>' in response.content


def test_brand_icon_is_discoverable():
    """Find the approved brand icon through Django staticfiles."""
    assert finders.find("images/aether_logo.png") is not None


def test_header_stylesheet_is_discoverable():
    """Expose the shared header stylesheet through Django staticfiles."""
    assert finders.find("css/components/header.css") is not None


def test_base_stylesheet_is_discoverable():
    """Expose the base stylesheet through Django staticfiles."""
    assert finders.find("css/base.css") is not None


def test_favicons_are_discoverable():
    """Ensure favicon assets are available through staticfiles."""
    assets = (
        "favicons/favicon.ico",
        "favicons/favicon-16x16.png",
        "favicons/favicon-32x32.png",
        "favicons/android-chrome-192x192.png",
        "favicons/android-chrome-512x512.png",
        "favicons/apple-touch-icon.png",
        "favicons/site.webmanifest",
    )

    for asset in assets:
        assert finders.find(asset) is not None
