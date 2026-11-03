"""Tests for the PostgreSQL public request counter maintenance command."""

from datetime import timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from accounts.models import PublicRequestCounter


pytestmark = pytest.mark.django_db


def _counter(key, expires_at):
    """Create a synthetic rate-limit row with a controlled deadline."""
    return PublicRequestCounter.objects.create(
        key=key,
        attempts=1,
        expires_at=expires_at,
    )


def test_cleanup_preserves_active_counters_and_removes_expired_ones():
    """Delete expired rows, retaining future windows."""
    now = timezone.now()
    _counter("expired", now - timedelta(hours=1))
    _counter("active", now + timedelta(hours=1))
    output = StringIO()

    call_command("prune_public_request_counters", stdout=output)

    remaining = set(PublicRequestCounter.objects.values_list("key", flat=True))
    assert remaining == {"active"}
    assert "Removed 1 expired public request counters." in output.getvalue()


def test_cleanup_uses_small_batches():
    """Delete more than one batch without losing active rows."""
    now = timezone.now()
    for index in range(3):
        _counter(str(index), now - timedelta(seconds=index + 1))
    _counter("active", now + timedelta(minutes=2))

    call_command(
        "prune_public_request_counters", batch_size=1, stdout=StringIO()
    )

    remaining = list(
        PublicRequestCounter.objects.values_list("key", flat=True)
    )
    assert remaining == ["active"]


def test_dry_run_reports_expired_rows_without_deleting():
    """Show the candidate count without modifying any counter rows."""
    _counter("expired", timezone.now() - timedelta(minutes=1))
    output = StringIO()

    call_command(
        "prune_public_request_counters", dry_run=True, stdout=output
    )

    assert "1 expired public request counters would be removed." in (
        output.getvalue()
    )
    assert PublicRequestCounter.objects.count() == 1


def test_cleanup_with_no_expired_counters():
    """Complete successfully when there are no rows to remove."""
    output = StringIO()

    call_command("prune_public_request_counters", stdout=output)

    assert "Removed 0 expired public request counters." in output.getvalue()


def test_invalid_batch_size_is_rejected():
    """Reject unsafe non-positive batch sizes."""
    with pytest.raises(CommandError, match="positive integer"):
        call_command("prune_public_request_counters", batch_size=0)
