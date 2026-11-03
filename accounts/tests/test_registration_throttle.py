"""HTTP enforcement of PostgreSQL-backed registration request limits."""

from datetime import UTC, datetime
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import override_settings
from django.urls import reverse

from accounts.models import PublicRequestCounter
from accounts.public_rate_limits import (
    PublicRequestAction,
    public_request_retry_after,
)
from accounts.tests.registration_helpers import registration_data


pytestmark = pytest.mark.django_db
TEST_ADDRESS = "192.0.2.70"


@pytest.fixture(autouse=True)
def enable_registration(settings):
    """Enable the staged registration route for this test module only."""
    settings.REGISTRATION_ENABLED = True


def _invalid_post(client, *, address=TEST_ADDRESS, **headers):
    """Submit an invalid form so requests have no account side effects."""
    return client.post(
        reverse("register"),
        registration_data(password2="not-the-same-password"),
        REMOTE_ADDR=address,
        **headers,
    )


def test_allowed_attempts_include_invalid_submissions(client):
    """Count invalid form submissions before reaching the creation path."""
    for _ in range(10):
        response = _invalid_post(client)
        assert response.status_code == 200

    assert PublicRequestCounter.objects.get().attempts == 10
    assert get_user_model().objects.count() == 0


def test_eleventh_attempt_returns_429_without_creating_an_account(client):
    """Deny a valid submission after exhausting its IP allowance."""
    for _ in range(10):
        _invalid_post(client)

    response = client.post(
        reverse("register"),
        registration_data(),
        REMOTE_ADDR=TEST_ADDRESS,
    )

    assert response.status_code == 429
    assert 0 < int(response["Retry-After"]) <= 3600
    assert response["Cache-Control"] == "no-store"
    assert b"Too many registration attempts" in response.content
    assert PublicRequestCounter.objects.get().attempts == 10
    assert not get_user_model().objects.exists()
    assert len(mail.outbox) == 0


def test_allowed_request_still_creates_an_account(client):
    """Preserve registration and delivery within the IP allowance."""
    response = client.post(
        reverse("register"),
        registration_data(),
        REMOTE_ADDR=TEST_ADDRESS,
    )

    assert response.status_code == 302
    assert response.url == reverse("registration_check_email")
    assert get_user_model().objects.filter(username="test-member").exists()
    assert PublicRequestCounter.objects.get().attempts == 1
    assert len(mail.outbox) == 1


def test_other_client_address_has_independent_allowance(client):
    """Do not share counters across distinct client IP addresses."""
    for _ in range(10):
        _invalid_post(client)

    assert _invalid_post(client, address="198.51.100.21").status_code == 200
    assert PublicRequestCounter.objects.count() == 2


def test_forwarded_for_does_not_override_development_client_ip(client):
    """Ignore untrusted forwarded headers in local development."""
    for number in range(10):
        response = _invalid_post(
            client,
            HTTP_X_FORWARDED_FOR=f"198.51.100.{number + 1}",
        )
        assert response.status_code == 200

    assert _invalid_post(
        client, HTTP_X_FORWARDED_FOR="203.0.113.10"
    ).status_code == 429
    assert PublicRequestCounter.objects.count() == 1


def test_missing_client_ip_fails_closed(client):
    """Never permit unmetered registration without a client address."""
    response = client.post(
        reverse("register"),
        registration_data(),
        REMOTE_ADDR="",
    )
    assert response.status_code == 503
    assert response["Cache-Control"] == "no-store"
    assert not PublicRequestCounter.objects.exists()
    assert not get_user_model().objects.exists()


def test_disabled_registration_does_not_consume_allowances(client):
    """Retain the existing 405 response ahead of request accounting."""
    with override_settings(REGISTRATION_ENABLED=False):
        response = _invalid_post(client)

    assert response.status_code == 405
    assert not PublicRequestCounter.objects.exists()


def test_registration_get_does_not_consume_allowances(client):
    """Allow the public GET page without consuming POST allowances."""
    assert client.get(reverse("register")).status_code == 200
    assert not PublicRequestCounter.objects.exists()


def test_retry_after_uses_the_next_utc_window():
    """Report the actual remaining duration of the hourly window."""
    sample_time = datetime(2026, 11, 3, 10, 15, tzinfo=UTC)
    with patch(
        "accounts.public_rate_limits.timezone.now", return_value=sample_time
    ):
        result = public_request_retry_after(PublicRequestAction.REGISTER_IP)

    assert result == 2700
