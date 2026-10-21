"""Tests for Aether authentication lockout helpers."""

from datetime import timedelta

import pytest
from asgiref.sync import async_to_sync
from axes.models import AccessAttempt
from django.contrib.auth import aauthenticate
from django.test import RequestFactory
from django.urls import reverse
from django.utils import timezone

from accounts.lockouts import get_lockout_username
from accounts.models import User

CLIENT_IP = "192.0.2.10"
OTHER_IP = "192.0.2.20"


@pytest.fixture(name="member")
def create_member():
    """Create an account with Django Admin access."""
    return User.objects.create_user(
        username="Aether.Member",
        email="member@example.test",
        password="test-password",
        is_staff=True,
    )


def login_attempt(client, identifier, password, ip=CLIENT_IP):
    """Submit credentials through the Django Admin login view."""
    return client.post(
        reverse("admin:login"),
        {
            "username": identifier,
            "password": password,
            "next": reverse("admin:index"),
        },
        REMOTE_ADDR=ip,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "identifier",
    [
        "Aether.Member",
        "aether.member",
        "AETHER.MEMBER",
        "member@example.test",
        "MEMBER@EXAMPLE.TEST",
    ],
)
def test_identifiers_share_lockout_identity(member, identifier):
    """Resolve username and email forms to a common identity."""
    request = RequestFactory().post("/admin/login/")

    assert get_lockout_username(
        request,
        {"username": identifier},
    ) == member.username.casefold()


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("identifier", "expected"),
    [
        ("Unknown.User", "unknown.user"),
        ("UNKNOWN@EXAMPLE.TEST", "unknown@example.test"),
    ],
)
def test_unknown_identifiers_are_case_insensitive(identifier, expected):
    """Normalise unknown identifiers without creating accounts."""
    request = RequestFactory().post("/admin/login/")

    assert get_lockout_username(
        request,
        {"username": identifier},
    ) == expected


@pytest.mark.django_db
def test_identifier_can_be_read_from_request():
    """Support Axes requests without an explicit credentials dictionary."""
    request = RequestFactory().post(
        "/admin/login/",
        {"username": "UNKNOWN@EXAMPLE.TEST"},
    )

    assert get_lockout_username(request) == "unknown@example.test"


def test_missing_identifier_returns_empty_string():
    """Handle requests without an account identifier."""
    request = RequestFactory().post("/admin/login/")

    assert get_lockout_username(request) == ""
    assert get_lockout_username(request, {}) == ""


def test_invalid_identifier_type_returns_empty_string():
    """Reject non-string credential values."""
    request = RequestFactory().post("/admin/login/")

    assert get_lockout_username(
        request,
        {"username": None},
    ) == ""


# ---------------------------------------------------------------------------
# Authentication lockout integration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_third_failure_locks_account(client, member):
    """Lock the account and IP combination on the third failure."""
    for _ in range(2):
        response = login_attempt(
            client, member.username, "wrong-password"
        )
        assert response.status_code == 200

    response = login_attempt(
        client, member.username, "wrong-password"
    )

    assert response.status_code == 429

    attempt = AccessAttempt.objects.get(
        username=member.username.casefold(),
        ip_address=CLIENT_IP,
    )
    assert attempt.failures_since_start == 3


@pytest.mark.django_db
def test_username_and_email_share_failure_count(client, member):
    """Prevent switching identifiers to bypass the failure limit."""
    identifiers = [
        member.username,
        member.email.upper(),
        member.username.upper(),
    ]

    for identifier in identifiers[:2]:
        response = login_attempt(
            client, identifier, "wrong-password"
        )
        assert response.status_code == 200

    response = login_attempt(
        client, identifiers[2], "wrong-password"
    )

    assert response.status_code == 429

    attempts = AccessAttempt.objects.filter(
        username=member.username.casefold(),
        ip_address=CLIENT_IP,
    )
    assert attempts.count() == 1
    assert attempts.get().failures_since_start == 3


@pytest.mark.django_db
def test_correct_password_cannot_bypass_lockout(client, member):
    """Reject correct credentials while the account remains locked."""
    for _ in range(3):
        login_attempt(
            client, member.username, "wrong-password"
        )

    response = login_attempt(
        client, member.email, "test-password"
    )

    assert response.status_code == 429


@pytest.mark.django_db
def test_different_ip_is_independent(client, member):
    """Keep failure counters separate for different IP addresses."""
    for _ in range(3):
        login_attempt(
            client, member.username, "wrong-password"
        )

    response = login_attempt(
        client, member.email, "test-password", ip=OTHER_IP
    )

    assert response.status_code == 302
    assert response.url == reverse("admin:index")


@pytest.mark.django_db
def test_different_user_is_independent(client, member):
    """Do not block another account using the same IP."""
    other = User.objects.create_user(
        username="Aether.Other",
        email="other@example.test",
        password="test-password",
        is_staff=True,
    )

    for _ in range(3):
        login_attempt(
            client, member.username, "wrong-password"
        )

    response = login_attempt(
        client, other.username, "test-password"
    )

    assert response.status_code == 302
    assert response.url == reverse("admin:index")


@pytest.mark.django_db
def test_successful_login_resets_failure_count(client, member):
    """Clear previous failures after successful authentication."""
    for _ in range(2):
        response = login_attempt(
            client, member.username, "wrong-password"
        )
        assert response.status_code == 200

    response = login_attempt(
        client, member.email, "test-password"
    )
    assert response.status_code == 302

    assert not AccessAttempt.objects.filter(
        username=member.username.casefold(),
        ip_address=CLIENT_IP,
    ).exists()

    client.logout()

    for _ in range(2):
        response = login_attempt(
            client, member.username, "wrong-password"
        )
        assert response.status_code == 200

    response = login_attempt(
        client, member.username, "wrong-password"
    )
    assert response.status_code == 429


@pytest.mark.django_db
def test_attempts_during_lockout_do_not_extend_it(client, member):
    """Keep the original lockout deadline after repeated failures."""
    for _ in range(3):
        login_attempt(
            client, member.username, "wrong-password"
        )

    attempt = AccessAttempt.objects.get(
        username=member.username.casefold(),
        ip_address=CLIENT_IP,
    )
    original_time = attempt.attempt_time

    response = login_attempt(
        client, member.email, "wrong-password"
    )

    assert response.status_code == 429

    attempt.refresh_from_db()
    assert attempt.attempt_time == original_time
    assert attempt.failures_since_start == 3


@pytest.mark.django_db
def test_lockout_expires_after_fifteen_minutes(client, member):
    """Permit authentication after the configured cool-off period."""
    for _ in range(3):
        login_attempt(
            client, member.username, "wrong-password"
        )

    AccessAttempt.objects.filter(
        username=member.username.casefold(),
        ip_address=CLIENT_IP,
    ).update(
        attempt_time=(
            timezone.now()
            - timedelta(minutes=15, seconds=5)
        )
    )

    response = login_attempt(
        client, member.email, "test-password"
    )

    assert response.status_code == 302
    assert response.url == reverse("admin:index")


@pytest.mark.django_db
def test_unknown_identifiers_have_independent_counters(client):
    """Track unrelated unknown identifiers separately."""
    for _ in range(3):
        login_attempt(
            client, "unknown-one", "wrong-password"
        )

    response = login_attempt(
        client, "unknown-two", "wrong-password"
    )

    assert response.status_code == 200

    assert AccessAttempt.objects.filter(
        ip_address=CLIENT_IP,
    ).count() == 2


@pytest.mark.django_db
def test_lockout_is_not_global_for_same_ip(client, member):
    """Confirm a locked account does not block unrelated usernames."""
    for _ in range(3):
        login_attempt(
            client, member.username, "wrong-password"
        )

    response = login_attempt(
        client, "another-unknown-user", "wrong-password"
    )

    assert response.status_code == 200


@pytest.mark.django_db(transaction=True)
def test_async_authentication_succeeds_before_lockout(member):
    """Allow valid asynchronous authentication before any lockout."""
    request = RequestFactory().post(
        reverse("admin:login"),
        REMOTE_ADDR=CLIENT_IP,
    )

    user = async_to_sync(aauthenticate)(
        request=request,
        username=member.email,
        password="test-password",
    )

    assert user == member


@pytest.mark.django_db(transaction=True)
def test_async_authentication_respects_shared_lockout(member):
    """Enforce the same failure limit across asynchronous identifiers."""
    factory = RequestFactory()

    for identifier in [
        member.username,
        member.email,
        member.username.upper(),
    ]:
        request = factory.post(
            reverse("admin:login"),
            REMOTE_ADDR=CLIENT_IP,
        )

        assert async_to_sync(aauthenticate)(
            request=request,
            username=identifier,
            password="wrong-password",
        ) is None

    attempt = AccessAttempt.objects.get(
        username=member.username.casefold(),
        ip_address=CLIENT_IP,
    )
    assert attempt.failures_since_start == 3

    request = factory.post(
        reverse("admin:login"),
        REMOTE_ADDR=CLIENT_IP,
    )

    assert async_to_sync(aauthenticate)(
        request=request,
        username=member.email,
        password="test-password",
    ) is None

    assert getattr(request, "axes_locked_out", False) is True

    attempt.refresh_from_db()
    assert attempt.failures_since_start == 3
