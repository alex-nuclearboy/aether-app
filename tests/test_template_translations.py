"""Ensure reusable and account templates can follow the active language."""

from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import translation


@pytest.mark.parametrize(
    ("language", "heading"),
    [
        ("en-gb", "Sign in to Aether"),
        ("pl", "Zaloguj się do Aether"),
        ("uk", "Увійти до Aether"),
    ],
)
def test_document_language_tracks_request_language(client, language, heading):
    """Render the requested HTML language and a project-specific string."""
    response = client.get(
        reverse("login"),
        HTTP_ACCEPT_LANGUAGE=language,
    )

    assert response.status_code == 200
    assert f'<html lang="{language}">'.encode() in response.content
    assert heading in response.content.decode()


@pytest.mark.parametrize(
    ("language", "heading"),
    [
        ("en-gb", "Verify your Aether email address"),
        ("pl", "Potwierdź swój adres e-mail w Aether"),
        ("uk", "Підтвердьте адресу електронної пошти в Aether"),
    ],
)
def test_verification_email_language_tracks_active_translation(
    language, heading
):
    """Render the email HTML and text in the active language."""
    with translation.override(language):
        html = render_to_string(
            "accounts/email/verification.html",
            {"verification_url": "https://example.test/verify/"},
        )

    assert f'<html lang="{language}">' in html
    assert f"<h1>{heading}</h1>" in html


@pytest.mark.parametrize(
    ("path", "marker"),
    [
        ("templates/includes/header.html", '{% trans "Sign in" %}'),
        ("templates/includes/header.html", '{% trans "Sign out" %}'),
        ("templates/components/messages.html", "{% trans 'Notifications' %}"),
        (
            "accounts/templates/accounts/login.html",
            '{% trans "Sign in to Aether" %}',
        ),
        ("core/templates/core/home.html", '{% trans "Home" %}'),
    ],
)
def test_public_template_labels_are_marked_for_translation(path, marker):
    """Prevent new untranslated literals in key shared UI locations."""
    source = (Path(settings.BASE_DIR) / path).read_text(encoding="utf-8")

    assert marker in source
