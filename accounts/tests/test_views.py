"""Integration tests for application login and logout."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from axes.models import AccessAttempt
from django.contrib.auth import SESSION_KEY
from django.test import Client
from django.urls import resolve, reverse
from django.utils import timezone

from accounts.audit import identifier_fingerprint
from accounts.forms import AetherAuthenticationForm
from accounts.models import User
from accounts.views import AetherLoginView


@pytest.fixture(name="member")
def create_member():
    """Create one application user without admin privileges."""
    return User.objects.create_user(
        username="login.member",
        email="login.member@example.test",
        password="correct-password",
    )


def test_application_authentication_urls_are_registered():
    """Expose explicit application login and logout endpoints."""
    login_url = reverse("login")
    logout_url = reverse("logout")

    assert login_url == "/login/"
    assert logout_url == "/logout/"
    assert resolve(login_url).func.view_class is AetherLoginView


def test_login_page_is_public_and_uses_shared_layout(client):
    """Render the account form through the existing Aether layout."""
    response = client.get(reverse("login"))

    assert response.status_code == 200
    template_names = [template.name for template in response.templates]
    assert "accounts/login.html" in template_names
    assert "base.html" in template_names
    assert isinstance(response.context["form"], AetherAuthenticationForm)
    assert b"Username or email" in response.content
    assert b'name="csrfmiddlewaretoken"' in response.content
    assert b"css/pages/login.css" in response.content
    assert response["X-Request-ID"]


def test_public_header_has_login_link(client):
    """Give anonymous visitors an application login entry point."""
    response = client.get(reverse("home"))

    assert response.status_code == 200
    assert b'href="/login/"' in response.content
    assert b"Sign in" in response.content
    assert b"Sign out" not in response.content


@pytest.mark.parametrize(
    "identifier",
    [
        "LOGIN.MEMBER",
        "LOGIN.MEMBER@EXAMPLE.TEST",
    ],
)
@pytest.mark.django_db
def test_login_accepts_username_or_email(client, member, identifier):
    """Authenticate case-insensitively with the existing backend."""
    response = client.post(
        reverse("login"),
        {"username": identifier, "password": "correct-password"},
        REMOTE_ADDR="192.0.2.101",
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("home")
    assert response["X-Request-ID"]
    assert str(client.session[SESSION_KEY]) == str(member.pk)


@pytest.mark.django_db
def test_login_shows_neutral_validation_error(client, member):
    """Avoid revealing whether the account or password was incorrect."""
    response = client.post(
        reverse("login"),
        {"username": member.email, "password": "wrong-password"},
        REMOTE_ADDR="192.0.2.102",
    )

    assert response.status_code == 200
    assert b"Please enter a valid username or email" in response.content
    assert b"case-sensitive" not in response.content
    assert SESSION_KEY not in client.session


@pytest.mark.django_db
def test_failed_login_uses_existing_audit(client, member):
    """Record a shared fingerprint without disclosing the identifier."""
    with patch("accounts.audit.logger.info") as audit_log:
        response = client.post(
            reverse("login"),
            {
                "username": member.email.upper(),
                "password": "wrong-password",
            },
            REMOTE_ADDR="192.0.2.109",
        )

    assert response.status_code == 200
    audit_log.assert_called_once()
    message, fingerprint, client_ip = audit_log.call_args.args
    assert message == (
        "authentication.login_failed identifier_hash=%s client_ip=%s"
    )
    assert fingerprint == identifier_fingerprint(member.username)
    assert client_ip == "192.0.2.109"
    assert member.username not in message
    assert member.email not in message


@pytest.mark.django_db
def test_login_rejects_inactive_member(client, member):
    """Continue to apply the existing inactive-account restriction."""
    member.is_active = False
    member.save(update_fields=["is_active"])

    response = client.post(
        reverse("login"),
        {"username": member.username, "password": "correct-password"},
        REMOTE_ADDR="192.0.2.103",
    )

    assert response.status_code == 200
    assert SESSION_KEY not in client.session


@pytest.mark.django_db
def test_login_preserves_internal_next_target(client, member):
    """Return to an internal destination requested before login."""
    url = f'{reverse("login")}?next=%2Fadmin%2F'
    get_response = client.get(url)

    assert b'name="next" value="/admin/"' in get_response.content

    response = client.post(
        reverse("login"),
        {
            "username": member.username,
            "password": "correct-password",
            "next": "/admin/",
        },
        REMOTE_ADDR="192.0.2.104",
    )

    assert response.status_code == 302
    assert response["Location"] == "/admin/"


@pytest.mark.parametrize(
    "target",
    [
        "https://external.example.test/phishing",
        "//external.example.test/phishing",
    ],
)
@pytest.mark.django_db
def test_login_rejects_external_next(client, member, target):
    """Do not permit an attacker-controlled login redirect."""
    response = client.post(
        reverse("login"),
        {
            "username": member.username,
            "password": "correct-password",
            "next": target,
        },
        REMOTE_ADDR="192.0.2.105",
    )

    assert response.status_code == 302
    assert response["Location"] == reverse("home")


@pytest.mark.django_db
def test_authenticated_header_uses_post_for_logout(client, member):
    """Expose logout as a CSRF-protected form, not a GET link."""
    client.force_login(member)

    response = client.get(reverse("home"))

    assert b'action="/logout/"' in response.content
    assert b'method="post"' in response.content
    assert b'name="csrfmiddlewaretoken"' in response.content
    assert b"Sign out" in response.content
    assert b'href="/login/"' not in response.content


@pytest.mark.django_db
def test_logout_requires_post_and_clears_session(client, member):
    """Preserve Django's POST-only logout and invalidate the session."""
    client.force_login(member)

    get_response = client.get(reverse("logout"))
    assert get_response.status_code == 405
    assert str(client.session[SESSION_KEY]) == str(member.pk)

    response = client.post(reverse("logout"))
    assert response.status_code == 302
    assert response["Location"] == reverse("home")
    assert SESSION_KEY not in client.session


@pytest.mark.django_db
def test_login_and_logout_enforce_csrf(member):
    """Reject unsafe POST requests without an actual CSRF token."""
    browser = Client(enforce_csrf_checks=True)

    no_token = browser.post(
        reverse("login"),
        {"username": member.username, "password": "correct-password"},
    )
    assert no_token.status_code == 403
    assert SESSION_KEY not in browser.session

    browser.force_login(member)
    no_token = browser.post(reverse("logout"))
    assert no_token.status_code == 403
    assert str(browser.session[SESSION_KEY]) == str(member.pk)


@pytest.mark.django_db
def test_application_lockout_and_repeated_denial(client, member):
    """Reuse Axes, audit signals, and dynamic Retry-After on the login page."""
    credentials = {
        "username": member.username,
        "password": "wrong-password",
    }
    ip_address = "192.0.2.106"

    with patch("accounts.audit.logger.warning") as warning_log:
        for expected_status in (200, 200, 429):
            response = client.post(
                reverse("login"), credentials, REMOTE_ADDR=ip_address
            )
            assert response.status_code == expected_status

        assert warning_log.call_count == 1
        assert warning_log.call_args.args[0].startswith(
            "authentication.lockout "
        )
        assert response["Cache-Control"] == "no-store"
        assert 0 < int(response["Retry-After"]) <= 900
        assert response["X-Request-ID"]

        attempt = AccessAttempt.objects.get(
            username=member.username.casefold(),
            ip_address=ip_address,
        )
        shifted = timezone.now() - timedelta(minutes=7)
        AccessAttempt.objects.filter(pk=attempt.pk).update(
            attempt_time=shifted
        )
        denied = client.post(
            reverse("login"),
            {
                "username": member.email.upper(),
                "password": "correct-password",
            },
            REMOTE_ADDR=ip_address,
        )

    assert denied.status_code == 429
    assert 470 <= int(denied["Retry-After"]) <= 480
    assert warning_log.call_count == 2
    assert warning_log.call_args_list[1].args[0].startswith(
        "authentication.lockout_denied "
    )
    assert warning_log.call_args_list[1].args[-1] == int(
        denied["Retry-After"]
    )
    assert SESSION_KEY not in client.session


@pytest.mark.django_db
def test_lockout_is_shared_between_admin_and_application(client, member):
    """Use one Axes failure counter across both authentication pages."""
    credentials = {
        "username": member.username,
        "password": "wrong-password",
    }
    ip_address = "192.0.2.107"
    for _ in range(2):
        response = client.post(
            reverse("admin:login"), credentials, REMOTE_ADDR=ip_address
        )
        assert response.status_code == 200

    locked = client.post(
        reverse("login"), credentials, REMOTE_ADDR=ip_address
    )

    assert locked.status_code == 429
    assert int(locked["Retry-After"]) > 0


@pytest.mark.django_db
def test_login_and_logout_use_existing_audit(client, member):
    """Keep application authentication in the shared audit pipeline."""
    with patch("accounts.audit.logger.info") as audit_log:
        login_response = client.post(
            reverse("login"),
            {
                "username": member.email.upper(),
                "password": "correct-password",
            },
            REMOTE_ADDR="192.0.2.108",
        )
        logout_response = client.post(
            reverse("logout"), REMOTE_ADDR="192.0.2.108"
        )

    assert login_response.status_code == 302
    assert logout_response.status_code == 302
    assert audit_log.call_count == 2
    assert audit_log.call_args_list[0].args[1] == member.pk
    assert audit_log.call_args_list[1].args[1] == member.pk
    assert audit_log.call_args_list[0].args[0].startswith(
        "authentication.login_success "
    )
    assert audit_log.call_args_list[1].args[0].startswith(
        "authentication.logout "
    )
    assert audit_log.call_args_list[0].args[2] == (
        audit_log.call_args_list[1].args[2]
    )
