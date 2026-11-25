"""Exercise real HTTP language selection and its security boundaries."""

from pathlib import Path

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.staticfiles import finders
from django.test import Client
from django.urls import reverse


@pytest.mark.parametrize("language", ["en-gb", "uk", "pl"])
def test_language_switch_sets_cookie_and_html_language(client, language):
    """Keep the chosen language across the redirect and next request."""
    home = reverse("home")
    response = client.post(
        reverse("set_language"),
        {"language": language},
        HTTP_REFERER=f"http://testserver{home}",
    )

    assert response.status_code == 302
    assert response["Location"] == f"http://testserver{home}"
    assert response.cookies[settings.LANGUAGE_COOKIE_NAME].value == language
    page = client.get(home)
    assert f'<html lang="{language}">'.encode() in page.content


def test_cookie_language_takes_precedence_over_accept_language(client):
    """A saved choice beats the browser's initial language header."""
    client.post(reverse("set_language"), {"language": "uk"})
    response = client.get(
        reverse("home"), HTTP_ACCEPT_LANGUAGE="pl"
    )

    assert b'<html lang="uk">' in response.content


def test_switch_is_csrf_protected():
    """The built-in language endpoint must not accept untrusted POSTs."""
    client = Client(enforce_csrf_checks=True)
    client.get(reverse("home"))

    response = client.post(
        reverse("set_language"), {"language": "pl"}
    )

    assert response.status_code == 403
    assert settings.LANGUAGE_COOKIE_NAME not in response.cookies


def test_switch_does_not_redirect_to_another_host(client):
    """Reject an untrusted next URL without an open redirect."""
    response = client.post(
        reverse("set_language"),
        {"language": "pl", "next": "https://invalid.example.test/"},
        HTTP_REFERER="http://testserver/",
    )

    assert response.status_code == 302
    assert response["Location"] == f"http://testserver{reverse('home')}"


def test_unsupported_cookie_language_falls_back(client):
    """Ignore unsupported locales instead of enabling extra languages."""
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "fr"
    response = client.get(
        reverse("home"), HTTP_ACCEPT_LANGUAGE="en-gb"
    )

    assert b'<html lang="en-gb">' in response.content


@pytest.mark.django_db
def test_switch_preserves_authenticated_session(client):
    """Changing a language must not sign an existing user out."""
    user = get_user_model().objects.create_user(
        username="locale-member",
        email="locale-member@example.test",
        password="Synthetic-Password-2026!",
    )
    client.force_login(user)
    response = client.post(
        reverse("set_language"), {"language": "pl"}
    )

    assert response.status_code == 302
    page = client.get(reverse("profile"))
    assert page.status_code == 200
    assert b'<html lang="pl">' in page.content


def test_header_offers_three_languages_and_csrf_token(client):
    """Offer one selection form with a CSRF-protected POST."""
    response = client.get(reverse("home"))
    html = response.content.decode()

    assert response.status_code == 200
    assert f'action="{reverse("set_language")}"' in html
    assert 'method="post"' in html
    assert 'name="csrfmiddlewaretoken"' in html
    assert 'name="language"' in html
    for code in ("en-gb", "uk", "pl"):
        assert f'value="{code}"' in html


def test_language_selection_keeps_existing_account_paths(client):
    """Leave account, reset, and verification URLs unprefixed."""
    client.post(reverse("set_language"), {"language": "uk"})

    assert reverse("login") == "/login/"
    assert reverse("register") == "/register/"
    assert reverse("password_reset") == "/password/reset/"
    assert reverse("profile") == "/profile/"


def test_language_selection_uses_native_labels(client):
    """Display recognisable choices before custom translations exist."""
    html = client.get(reverse("home")).content.decode()

    for label in ("English (UK)", "Українська", "Polski"):
        assert label in html


def test_language_picker_auto_submits_without_visible_apply_button(client):
    """Use a change event to submit while retaining a no-JS fallback."""
    html = client.get(reverse("home")).content.decode()

    assert 'js/language-switch.js' in html
    assert 'defer></script>' in html
    assert 'Language (changes immediately)' in html
    assert '<noscript>' in html
    assert '</noscript>' in html
    assert 'onchange=' not in html

    asset = finders.find('js/language-switch.js')
    assert asset is not None
    script = Path(asset).read_text(encoding='utf-8')
    assert 'addEventListener("change"' in script
    assert 'requestSubmit()' in script
