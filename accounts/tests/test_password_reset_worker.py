"""Password reset worker retry, expiry and command regression tests."""

from datetime import timedelta
from io import StringIO
from smtplib import SMTPException
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from accounts.email_worker import DeliveryOutcome
from accounts.models import PasswordResetEmailJob, User
from accounts.password_reset import request_password_reset_email
from accounts.password_reset_worker import (
    deliver_next_password_reset_email,
)


pytestmark = pytest.mark.django_db
ORIGIN = "https://aether.example.test"


@pytest.fixture(name="member")
def create_member():
    """Create a trusted account eligible for password recovery."""
    return User.objects.create_user(
        username="password-worker-member",
        email="reset-worker@example.test",
        password="Example-Strong-Passphrase-719!",
        email_verification_required=True,
        verified_email="reset-worker@example.test",
    )


def test_empty_worker_queue_returns_idle():
    """Keep an empty queue free of artificial delivery work."""
    assert deliver_next_password_reset_email(ORIGIN) is None


def test_transport_failure_is_retried(member):
    """Apply bounded retry to SMTP exceptions."""
    request_password_reset_email(member.email)
    with patch(
        "accounts.emails.EmailMultiAlternatives.send",
        side_effect=SMTPException("private diagnostic"),
    ):
        assert deliver_next_password_reset_email(ORIGIN) == (
            DeliveryOutcome.RETRY
        )
    job = PasswordResetEmailJob.objects.get(user=member)
    assert job.status == PasswordResetEmailJob.Status.PENDING
    assert job.attempts == 1
    assert job.last_error_code == "transport"
    assert job.available_at > timezone.now()
    assert not mail.outbox


def test_unexpected_preparation_error_is_retried(member):
    """Unexpected message-building failures must not stop the worker."""
    request_password_reset_email(member.email)
    with patch(
        "accounts.password_reset_worker.build_password_reset_message",
        side_effect=RuntimeError("private reset token"),
    ):
        assert deliver_next_password_reset_email(ORIGIN) == (
            DeliveryOutcome.RETRY
        )
    assert PasswordResetEmailJob.objects.get().last_error_code == (
        "preparation"
    )


def test_unexpected_delivery_error_is_retried_without_logging_secrets(
    member,
):
    """Retry backend faults and log the exception type, not its details."""
    request_password_reset_email(member.email)
    with (
        patch(
            "accounts.password_reset_worker.send_email_message",
            side_effect=RuntimeError("private reset URL"),
        ),
        patch("accounts.password_reset_worker.logger.error") as log_error,
    ):
        result = deliver_next_password_reset_email(ORIGIN)
    assert result == DeliveryOutcome.RETRY
    job = PasswordResetEmailJob.objects.get(user=member)
    assert job.status == PasswordResetEmailJob.Status.PENDING
    assert job.attempts == 1
    assert job.last_error_code == "delivery"
    assert job.available_at > timezone.now()
    assert not mail.outbox
    log_error.assert_called_once()
    assert "private reset URL" not in str(log_error.call_args)
    assert "RuntimeError" in str(log_error.call_args)


def test_missing_account_cancels_claimed_reset_job(member):
    """Do not deliver a reset link when the user lookup fails."""
    request_password_reset_email(member.email)
    with patch(
        "accounts.email_worker.User.objects.get",
        side_effect=User.DoesNotExist,
    ):
        outcome = deliver_next_password_reset_email(ORIGIN)
    assert outcome == DeliveryOutcome.CANCELLED
    job = PasswordResetEmailJob.objects.get(user=member)
    assert job.status == PasswordResetEmailJob.Status.CANCELLED
    assert job.last_error_code == "missing_user"
    assert job.lease_expires_at is None
    assert not mail.outbox


def test_exhausted_job_is_failed(member):
    """Retire a fifth failed delivery after the bounded retry limit."""
    request_password_reset_email(member.email)
    PasswordResetEmailJob.objects.update(attempts=4)
    with patch(
        "accounts.emails.EmailMultiAlternatives.send",
        side_effect=OSError("no delivery"),
    ):
        assert deliver_next_password_reset_email(ORIGIN) == (
            DeliveryOutcome.FAILED
        )
    job = PasswordResetEmailJob.objects.get()
    assert job.attempts == 5
    assert job.status == PasswordResetEmailJob.Status.FAILED


def test_expired_lease_is_reclaimed(member):
    """Recover a job whose original worker stopped during processing."""
    request_password_reset_email(member.email)
    PasswordResetEmailJob.objects.update(
        status=PasswordResetEmailJob.Status.PROCESSING,
        attempts=1,
        lease_expires_at=timezone.now() - timedelta(minutes=1),
    )
    assert deliver_next_password_reset_email(ORIGIN) == DeliveryOutcome.SENT
    assert PasswordResetEmailJob.objects.get().attempts == 2


@pytest.mark.django_db(transaction=True)
def test_one_shot_command_prints_console_email(member):
    """Keep production SMTP out of the HTTP request."""
    request_password_reset_email(member.email)
    output = StringIO()
    call_command(
        "process_password_reset_queue",
        "--once",
        "--public-origin=https://aether.example.test",
        stdout=output,
    )
    assert "sent" in output.getvalue()
    assert len(mail.outbox) == 1


@pytest.mark.django_db(transaction=True)
def test_one_shot_command_is_idle_with_no_jobs():
    """Exit cleanly when no work is waiting."""
    output = StringIO()
    call_command(
        "process_password_reset_queue",
        "--once",
        "--public-origin=https://aether.example.test",
        stdout=output,
    )
    assert "idle" in output.getvalue()


@pytest.mark.parametrize("interval", [0, -1, 301])
def test_reset_command_rejects_invalid_poll_interval(interval):
    """Preserve the same polling limits as verification delivery."""
    with pytest.raises(CommandError, match="poll-seconds"):
        call_command(
            "process_password_reset_queue",
            "--once",
            "--public-origin=https://aether.example.test",
            f"--poll-seconds={interval}",
        )


def test_one_shot_command_fails_safely():
    """Never disclose a reset token in an infrastructure exception."""
    with patch(
        "accounts.management.commands.process_password_reset_queue."
        "deliver_next_password_reset_email",
        side_effect=RuntimeError("private reset URL"),
    ):
        with pytest.raises(CommandError) as error:
            call_command(
                "process_password_reset_queue",
                "--once",
                "--public-origin=https://aether.example.test",
            )
    assert str(error.value) == "Password reset email processing failed."
    assert "private reset URL" not in str(error.value)
