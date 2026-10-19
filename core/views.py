"""Views for the Aether core application."""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def home(request: HttpRequest) -> HttpResponse:
    """Render the home page."""
    return render(request, "core/home.html")
