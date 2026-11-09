"""Management command tests for verification email queue delivery."""

from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from accounts.email_outbox import queue_verification_email
from accounts.models import User, VerificationEmailJob

pytestmark = pytest.mark.django_db


@pytest.mark.django_db(transaction=True)
def test_once_command_sends_one_queued_message(mailoutbox):
    """Exercise the independent worker without any HTTP request."""
    user = User.objects.create_user(
        username="worker-test",
        email="worker@example.com",
        password="ExamplePassphrase728!",
    )
    queue_verification_email(user.pk)
    output = StringIO()

    call_command(
        "process_verification_email_queue",
        "--once",
        "--public-origin=http://127.0.0.1:8000",
        stdout=output,
    )

    assert "sent" in output.getvalue()
    assert len(mailoutbox) == 1
    assert VerificationEmailJob.objects.get().status == (
        VerificationEmailJob.Status.SENT
    )


@pytest.mark.django_db(transaction=True)
def test_once_command_without_jobs_reports_idle():
    """An empty queue exits cleanly in inspection mode."""
    output = StringIO()
    call_command(
        "process_verification_email_queue",
        "--once",
        "--public-origin=http://127.0.0.1:8000",
        stdout=output,
    )
    assert "idle" in output.getvalue()


@pytest.mark.parametrize("interval", [0, -2, 301])
def test_command_rejects_invalid_poll_interval(interval):
    """Prevent busy loops and unreasonable idle delays."""
    with pytest.raises(CommandError, match="poll-seconds"):
        call_command(
            "process_verification_email_queue",
            "--once",
            "--public-origin=http://127.0.0.1:8000",
            f"--poll-seconds={interval}",
        )


def test_command_requires_public_origin():
    """Do not silently guess the public website from a server hostname."""
    with pytest.raises(CommandError):
        call_command("process_verification_email_queue", "--once")


@override_settings(ENVIRONMENT="production")
def test_command_rejects_http_origin_in_production():
    """Fail before claiming jobs if the public origin is not HTTPS."""
    with pytest.raises(CommandError, match="HTTPS"):
        call_command(
            "process_verification_email_queue",
            "--once",
            "--public-origin=http://example.com",
        )


def test_once_command_reports_unexpected_error_without_sensitive_data():
    """An infrastructure error is visible to one-shot automation."""
    with patch(
        "accounts.management.commands.process_verification_email_queue."
        "deliver_next_verification_email",
        side_effect=RuntimeError("private verification URL"),
    ):
        with pytest.raises(CommandError) as error:
            call_command(
                "process_verification_email_queue",
                "--once",
                "--public-origin=http://127.0.0.1:8000",
            )

    assert str(error.value) == "Verification email processing failed."
    assert "private verification URL" not in str(error.value)


def test_continuous_command_recovers_from_unexpected_error():
    """Keep polling after an infrastructure error with a safe pause."""
    with (
        patch(
            "accounts.management.commands.process_verification_email_queue."
            "deliver_next_verification_email",
            side_effect=[
                RuntimeError("private verification URL"), "sent", None,
            ],
        ) as delivery,
        patch(
            "accounts.management.commands.process_verification_email_queue."
            "sleep",
            side_effect=[None, KeyboardInterrupt],
        ) as pause,
        patch(
            "accounts.management.commands.process_verification_email_queue."
            "logger.error",
        ) as log_error,
    ):
        output = StringIO()
        call_command(
            "process_verification_email_queue",
            "--poll-seconds=1",
            "--public-origin=http://127.0.0.1:8000",
            stdout=output,
        )

    assert delivery.call_count == 3
    assert pause.call_count == 2
    assert pause.call_args_list[0].args == (5.0,)
    assert pause.call_args_list[1].args == (1.0,)
    log_error.assert_called_once()
    assert "RuntimeError" in str(log_error.call_args)
    assert "private verification URL" not in str(log_error.call_args)
    assert "worker stopped" in output.getvalue()


def test_continuous_command_stops_cleanly_on_keyboard_interrupt():
    """Poll after a successful delivery and stop cleanly on interruption."""
    with (
        patch(
            "accounts.management.commands.process_verification_email_queue."
            "deliver_next_verification_email",
            side_effect=["sent", None],
        ) as delivery,
        patch(
            "accounts.management.commands.process_verification_email_queue."
            "sleep",
            side_effect=KeyboardInterrupt,
        ) as pause,
    ):
        output = StringIO()
        call_command(
            "process_verification_email_queue",
            "--public-origin=http://127.0.0.1:8000",
            stdout=output,
        )

    assert delivery.call_count == 2
    pause.assert_called_once_with(5)
    assert "worker stopped" in output.getvalue()
