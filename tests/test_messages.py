"""Tests for shared flash messages and semantic appearance."""

from pathlib import Path

import pytest
from django.contrib import messages
from django.contrib.messages import constants as message_constants
from django.contrib.auth import SESSION_KEY
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.urls import reverse

from accounts.models import User


@pytest.mark.parametrize(
    ("level", "css_class"),
    [
        (messages.SUCCESS, "alert--success"),
        (messages.INFO, "alert--info"),
        (messages.WARNING, "alert--warning"),
        (messages.ERROR, "alert--error"),
    ],
)
def test_messages_component_uses_semantic_states(level, css_class):
    """Render each severity with a shared accessible component."""
    message = type("SampleMessage", (), {
        "level_tag": message_constants.DEFAULT_TAGS[level],
        "__str__": lambda self: "Example notification",
    })()
    html = render_to_string(
        "components/messages.html", {"messages": [message]}
    )

    assert css_class in html
    assert "Example notification" in html
    if level == messages.ERROR:
        assert 'role="alert"' in html
    else:
        assert 'role="status"' in html


def test_flash_stylesheet_is_available():
    """Expose shared message styles through staticfiles."""
    location = finders.find("css/components/alert.css")
    assert location is not None
    content = Path(location).read_text(encoding="utf-8")
    assert ".alert--success" in content
    assert ".alert--warning" in content
    assert ".alert--error" in content


@pytest.mark.django_db
def test_logout_displays_one_success_message(client):
    """Confirm logout without retaining authentication or stale messages."""
    user = User.objects.create_user(
        username="feedback.member",
        email="feedback.member@example.test",
        password="test-password",
    )
    client.force_login(user)

    response = client.post(reverse("logout"))
    assert response.status_code == 302
    assert SESSION_KEY not in client.session

    first = client.get(reverse("home"))
    assert b"You have signed out successfully." in first.content
    assert b"alert--success" in first.content

    second = client.get(reverse("home"))
    assert b"You have signed out successfully." not in second.content
