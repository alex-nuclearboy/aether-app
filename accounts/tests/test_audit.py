"""Tests for authentication audit events."""

from datetime import UTC, datetime, timedelta
from unittest.mock import call, patch

import pytest
from axes.models import AccessAttempt
from django.conf import settings
from django.urls import reverse
from django.utils.crypto import salted_hmac

from accounts.audit import audit_lockout, audit_logout
from accounts.models import User


@pytest.mark.django_db
def test_admin_login_and_logout_are_audited(client):
    """Record successful admin login and logout events."""
    user = User.objects.create_user(
        username="audit.member",
        email="audit.member@example.test",
        password="test-password",
        is_staff=True,
    )

    with patch("accounts.audit.logger.info") as log_info:
        login_response = client.post(
            reverse("admin:login"),
            {
                "username": user.username,
                "password": "test-password",
            },
            REMOTE_ADDR="192.0.2.10",
        )

        assert login_response.status_code == 302

        logout_response = client.post(
            reverse("admin:logout"),
            REMOTE_ADDR="192.0.2.10",
        )

        assert logout_response.status_code in (200, 302)

    assert log_info.call_args_list == [
        call(
            "authentication.login_success user_id=%s client_ip=%s",
            user.pk,
            "192.0.2.10",
        ),
        call(
            "authentication.logout user_id=%s client_ip=%s",
            user.pk,
            "192.0.2.10",
        ),
    ]


def test_anonymous_logout_is_not_audited(rf):
    """Do not record logout events without an authenticated user."""
    request = rf.post(
        "/admin/logout/",
        REMOTE_ADDR="192.0.2.10",
    )

    with patch("accounts.audit.logger.info") as log_info:
        audit_logout(request=request, user=None)

    log_info.assert_not_called()


@pytest.mark.django_db
def test_lockout_audit_records_deadline_once(client):
    """Record the lockout deadline without repeating the audit event."""
    user = User.objects.create_user(
        username="lockout.member",
        email="lockout.member@example.test",
        password="correct-password",
        is_staff=True,
    )

    with patch("accounts.audit.logger.warning") as log_warning:
        for index, identifier in enumerate(
            (user.username.upper(), user.email.upper(), user.username)
        ):
            response = client.post(
                reverse("admin:login"),
                {
                    "username": identifier,
                    "password": "incorrect-password",
                },
                REMOTE_ADDR="192.0.2.30",
            )

            assert response.status_code == (
                429 if index == 2 else 200
            )

        log_warning.assert_called_once()

        (
            message,
            identifier_hash,
            client_ip,
            failures,
            duration_seconds,
            retry_after_seconds,
            locked_until,
        ) = log_warning.call_args.args

        assert message == (
            "authentication.lockout identifier_hash=%s "
            "client_ip=%s failures=%s duration_seconds=%s "
            'retry_after_seconds=%s locked_until="%s"'
        )

        assert identifier_hash == salted_hmac(
            "aether.authentication.lockout",
            user.username.casefold(),
            algorithm="sha256",
        ).hexdigest()

        assert client_ip == "192.0.2.30"
        assert failures == 3
        assert duration_seconds == 900
        assert 0 < retry_after_seconds <= duration_seconds

        attempt = AccessAttempt.objects.get(
            username=user.username.casefold(),
            ip_address="192.0.2.30",
        )

        expected_deadline = (
            attempt.attempt_time + settings.AXES_COOLOFF_TIME
        ).astimezone(UTC).replace(microsecond=0)

        assert datetime.fromisoformat(
            locked_until
        ) == expected_deadline

        assert user.username not in str(log_warning.call_args)
        assert user.email not in str(log_warning.call_args)

        response = client.post(
            reverse("admin:login"),
            {
                "username": user.email,
                "password": "correct-password",
            },
            REMOTE_ADDR="192.0.2.30",
        )

        assert response.status_code == 429
        log_warning.assert_called_once()


@pytest.mark.parametrize(
    "missing",
    ["cool_off", "deadline"],
)
def test_lockout_audit_skips_unavailable_timing(rf, missing):
    """Do not record lockouts without valid timing information."""
    request = rf.post(
        "/admin/login/",
        REMOTE_ADDR="192.0.2.10",
    )
    request.axes_failures_since_start = settings.AXES_FAILURE_LIMIT

    cool_off = (
        None if missing == "cool_off" else timedelta(minutes=15)
    )
    deadline = (
        None if missing == "deadline" else datetime.now(UTC)
    )

    with (
        patch(
            "accounts.audit.get_cool_off",
            return_value=cool_off,
        ),
        patch(
            "accounts.audit.get_lockout_deadline",
            return_value=deadline,
        ),
        patch("accounts.audit.logger.warning") as log_warning,
    ):
        audit_lockout(
            request=request,
            username="lockout.member",
        )

    log_warning.assert_not_called()
