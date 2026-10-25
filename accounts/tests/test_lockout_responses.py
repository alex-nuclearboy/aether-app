"""Tests for Axes lockout responses and repeated-denial auditing."""

from datetime import timedelta
from unittest.mock import patch

import pytest
from axes.models import AccessAttempt
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone

from accounts.lockout_responses import lockout_response
from accounts.models import User


@pytest.mark.django_db
def test_lockout_response_recomputes_remaining_seconds(client):
    """Return a new Retry-After for each denied authentication attempt."""
    user = User.objects.create_user(
        username="response.member",
        email="response.member@example.test",
        password="correct-password",
        is_staff=True,
    )
    credentials = {"username": user.username, "password": "wrong-password"}
    url = reverse("admin:login")

    with (
        patch("accounts.lockout_responses.logger.warning") as warning,
        patch("accounts.audit.logger.info") as audit_info,
    ):
        for _ in range(2):
            response = client.post(
                url,
                credentials,
                REMOTE_ADDR="192.0.2.55",
            )
            assert response.status_code == 200
        assert audit_info.call_count == 2

        locked = client.post(url, credentials, REMOTE_ADDR="192.0.2.55")
        assert locked.status_code == 429
        assert 0 < int(locked["Retry-After"]) <= 900
        assert audit_info.call_count == 2
        assert client.get(url, REMOTE_ADDR="192.0.2.55").status_code == 200
        assert warning.call_count == 1
        assert warning.call_args_list[0].args[0].startswith(
            "authentication.lockout "
        )

        attempt = AccessAttempt.objects.get(
            username=user.username.casefold(),
            ip_address="192.0.2.55",
        )
        shifted_time = timezone.now() - timedelta(minutes=7)
        AccessAttempt.objects.filter(pk=attempt.pk).update(
            attempt_time=shifted_time,
        )

        denied = client.post(
            url,
            {"username": user.email.upper(), "password": "correct-password"},
            REMOTE_ADDR="192.0.2.55",
        )

    assert denied.status_code == 429
    assert audit_info.call_count == 2
    assert 470 <= int(denied["Retry-After"]) <= 480
    attempt.refresh_from_db()
    assert attempt.attempt_time == shifted_time
    assert denied["Cache-Control"] == "no-store"
    assert warning.call_count == 2
    fmt, fingerprint, ip, remaining = warning.call_args_list[1].args
    assert fmt == (
        "authentication.lockout_denied identifier_hash=%s "
        "client_ip=%s retry_after_seconds=%s"
    )
    assert len(fingerprint) == 64
    assert ip == "192.0.2.55"
    assert remaining == int(denied["Retry-After"])


def test_lockout_response_does_not_audit_get_requests(rf):
    """Page visits do not count as denied login attempts."""
    request = rf.get("/admin/login/", REMOTE_ADDR="192.0.2.56")
    with (
        patch(
            "accounts.lockout_responses.get_lockout_remaining_seconds",
            return_value=200,
        ),
        patch("accounts.lockout_responses.logger.warning") as warning,
    ):
        response = lockout_response(
            request,
            HttpResponse(), {"username": "unknown"},
        )
    assert response.status_code == 429
    assert response["Retry-After"] == "200"
    warning.assert_not_called()


def test_lockout_response_without_active_deadline(rf):
    """Do not invent a Retry-After when the deadline is unavailable."""
    request = rf.post("/admin/login/", REMOTE_ADDR="192.0.2.57")
    with (
        patch(
            "accounts.lockout_responses.get_lockout_remaining_seconds",
            return_value=0,
        ),
        patch("accounts.lockout_responses.logger.warning") as warning,
    ):
        response = lockout_response(
            request,
            HttpResponse(),
            {"username": None},
        )
    assert response.status_code == 429
    assert "Retry-After" not in response
    warning.assert_not_called()


@pytest.mark.parametrize(
    "credentials",
    [
        None,
        {"username": None},
    ],
)
def test_lockout_response_uses_post_identifier_as_fallback(rf, credentials):
    """Read the posted identifier when Axes credentials are unavailable."""
    request = rf.post(
        "/admin/login/",
        {"username": "POST.Member"},
        REMOTE_ADDR="192.0.2.58",
    )
    with (
        patch(
            "accounts.lockout_responses.get_lockout_remaining_seconds",
            return_value=120,
        ) as remaining,
        patch("accounts.lockout_responses.logger.warning") as warning,
    ):
        response = lockout_response(request, HttpResponse(), credentials)

    remaining.assert_called_once_with(request, "POST.Member")
    assert response.status_code == 429
    assert response["Retry-After"] == "120"
    assert warning.call_count == 1
    assert warning.call_args.args[0].startswith(
        "authentication.lockout_denied "
    )
    assert warning.call_args.args[2] == "192.0.2.58"


def test_lockout_response_does_not_audit_empty_identifier(rf):
    """Do not log a blocked attempt without a usable identifier."""
    request = rf.post("/admin/login/", REMOTE_ADDR="192.0.2.59")
    with (
        patch(
            "accounts.lockout_responses.get_lockout_remaining_seconds",
            return_value=120,
        ) as remaining,
        patch("accounts.lockout_responses.logger.warning") as warning,
    ):
        response = lockout_response(request, HttpResponse(), {"username": ""})

    remaining.assert_called_once_with(request, "")
    assert response.status_code == 429
    assert response["Retry-After"] == "120"
    warning.assert_not_called()
