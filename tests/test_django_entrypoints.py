"""Smoke tests for Django project entry points and URL configuration."""

from django.core.handlers.asgi import ASGIHandler
from django.core.handlers.wsgi import WSGIHandler
from django.urls import resolve, reverse

from config.asgi import application as asgi_application
from config.wsgi import application as wsgi_application


def test_asgi_application_is_configured() -> None:
    """Expose a valid Django ASGI application."""
    assert isinstance(asgi_application, ASGIHandler)


def test_wsgi_application_is_configured() -> None:
    """Expose a valid Django WSGI application."""
    assert isinstance(wsgi_application, WSGIHandler)


def test_admin_url_is_registered() -> None:
    """Expose the Django administration site at the expected URL."""
    admin_url = reverse("admin:index")
    match = resolve(admin_url)

    assert admin_url == "/admin/"
    assert match.app_name == "admin"
    assert match.url_name == "index"
