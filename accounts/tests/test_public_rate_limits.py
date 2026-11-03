"""PostgreSQL request-limit accounting and privacy tests."""

# Pylint does not recognise the dynamically exported executor.
# pylint: disable-next=no-name-in-module
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

import pytest
from django.db import close_old_connections, connections

from accounts.models import PublicRequestCounter
from accounts.public_rate_limits import (
    PublicRequestAction,
    consume_public_request,
)


pytestmark = pytest.mark.django_db
REFERENCE_TIME = datetime(2026, 11, 3, 10, tzinfo=UTC)


def test_registration_limit_rejects_the_eleventh_request():
    """Block attempts beyond the configured allowance in one window."""
    action = PublicRequestAction.REGISTER_IP
    for _ in range(10):
        assert consume_public_request(action, "192.0.2.17", now=REFERENCE_TIME)

    assert not consume_public_request(
        action, "192.0.2.17", now=REFERENCE_TIME
    )
    counter = PublicRequestCounter.objects.get()
    assert counter.attempts == 10
    assert counter.expires_at == REFERENCE_TIME + timedelta(hours=1)


def test_new_window_allows_new_requests():
    """Use distinct counters when the fixed UTC window changes."""
    action = PublicRequestAction.RESEND_EMAIL
    for _ in range(3):
        assert consume_public_request(
            action, "member@example.com", now=REFERENCE_TIME
        )
    assert not consume_public_request(
        action, "member@example.com", now=REFERENCE_TIME
    )
    assert consume_public_request(
        action, "member@example.com",
        now=REFERENCE_TIME + timedelta(hours=1),
    )
    assert PublicRequestCounter.objects.count() == 2


def test_different_actions_and_identities_are_independent():
    """Keep limits separate by operation and identifier."""
    assert consume_public_request(
        PublicRequestAction.RESEND_EMAIL,
        "member@example.com",
        now=REFERENCE_TIME,
    )
    assert consume_public_request(
        PublicRequestAction.RESEND_IP,
        "192.0.2.17",
        now=REFERENCE_TIME,
    )
    assert consume_public_request(
        PublicRequestAction.RESEND_EMAIL,
        "other@example.com",
        now=REFERENCE_TIME,
    )
    assert PublicRequestCounter.objects.count() == 3


def test_normalisation_and_privacy_of_stored_keys():
    """Case-fold identities but store only a keyed fingerprint."""
    action = PublicRequestAction.CORRECT_EMAIL_USERNAME
    assert consume_public_request(
        action, "  Example-Member  ", now=REFERENCE_TIME
    )
    assert consume_public_request(
        action, "example-member", now=REFERENCE_TIME
    )
    counter = PublicRequestCounter.objects.get()
    assert counter.attempts == 2
    assert len(counter.key) == 64
    assert "example-member" not in counter.key


@pytest.mark.parametrize(
    ("action", "identity", "now"),
    [
        ("unknown.action", "192.0.2.17", REFERENCE_TIME),
        (PublicRequestAction.RESEND_IP, "", REFERENCE_TIME),
        (PublicRequestAction.RESEND_IP, "   ", REFERENCE_TIME),
        (PublicRequestAction.RESEND_IP, "192.0.2.17", datetime(2026, 1, 1)),
    ],
)
def test_invalid_arguments_do_not_create_counters(action, identity, now):
    """Never silently allow missing identities or invalid policies."""
    with pytest.raises(ValueError):
        consume_public_request(action, identity, now=now)
    assert not PublicRequestCounter.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_simultaneous_requests_do_not_exceed_allowance():
    """Enforce an allowance across concurrent PostgreSQL connections."""
    action = PublicRequestAction.RESEND_EMAIL

    def request_allowance():
        close_old_connections()
        try:
            return consume_public_request(
                action, "member@example.com", now=REFERENCE_TIME
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = [pool.submit(request_allowance) for _ in range(8)]
        results = [future.result() for future in futures]

    assert sum(results) == 3
    assert PublicRequestCounter.objects.get().attempts == 3
