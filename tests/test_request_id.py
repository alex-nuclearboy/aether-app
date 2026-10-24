"""Tests for request correlation and logging isolation."""

import asyncio
import logging
from unittest.mock import patch

import pytest
from asgiref.sync import async_to_sync
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse

from accounts.models import User
from infrastructure.request_id import (
    RequestIdFilter,
    current_request_id,
    request_id_middleware,
)


def test_request_ids_are_unique_and_server_generated(rf):
    """Assign one trusted ID per request and restore outer context."""
    observed = []

    def view(request):
        observed.append(current_request_id.get())
        assert request.request_id == observed[-1]
        return HttpResponse("OK")

    middleware = request_id_middleware(view)
    first = middleware(rf.get("/", HTTP_X_REQUEST_ID="spoofed"))
    second = middleware(rf.get("/"))
    assert first["X-Request-ID"] != second["X-Request-ID"]
    assert first["X-Request-ID"] != "spoofed"
    assert all(len(value) == 32 for value in observed)
    assert observed == [first["X-Request-ID"], second["X-Request-ID"]]
    assert current_request_id.get() == "-"


def test_filter_exposes_scoped_id_and_default(rf):
    """Use default outside requests and actual ID inside requests."""
    def record_id():
        record = logging.LogRecord(
            "aether.test", logging.INFO, __file__, 1, "test", (), None
        )
        assert RequestIdFilter().filter(record)
        return record.request_id

    assert record_id() == "-"
    observed = []

    def view(_request):
        observed.append(record_id())
        return HttpResponse("OK")

    response = request_id_middleware(view)(rf.get("/"))
    assert observed == [response["X-Request-ID"]]
    assert record_id() == "-"


def test_rate_limit_creates_correlated_http_event(rf):
    """Log HTTP 429 while its request ID is still active."""
    observed = []

    def fake_log(level, *_args):
        observed.append((level, current_request_id.get()))

    with patch("infrastructure.request_id.http_logger.log", fake_log):
        response = request_id_middleware(
            lambda _request: HttpResponse(status=429)
        )(rf.post("/admin/login/"))

    assert observed == [(logging.WARNING, response["X-Request-ID"])]


@pytest.mark.parametrize(
    ("status_code", "expected_level"),
    [
        (200, logging.INFO),
        (302, logging.INFO),
        (404, logging.INFO),
        (429, logging.WARNING),
        (500, logging.ERROR),
    ],
)
def test_http_response_logging_levels(
    rf,
    status_code,
    expected_level,
):
    """Log HTTP responses at the appropriate severity."""
    with patch("infrastructure.request_id.http_logger.log") as mock_log:
        response = request_id_middleware(
            lambda _request: HttpResponse(status=status_code)
        )(rf.get("/test/"))

    assert response.status_code == status_code
    mock_log.assert_called_once_with(
        expected_level,
        "http.response method=%s path=%s status_code=%s",
        "GET",
        "/test/",
        status_code,
    )


def test_context_is_reset_when_processing_raises(rf):
    """Avoid leaking an ID into later requests after errors."""
    def failing(_request):
        raise RuntimeError("test failure")

    with pytest.raises(RuntimeError, match="test failure"):
        request_id_middleware(failing)(rf.get("/"))
    assert current_request_id.get() == "-"


def test_async_middleware_keeps_id_across_await(rf):
    """Maintain context during asynchronous request processing."""
    observed = []

    async def view(_request):
        observed.append(current_request_id.get())
        await asyncio.sleep(0)
        observed.append(current_request_id.get())
        return HttpResponse("OK")

    response = async_to_sync(request_id_middleware(view))(rf.get("/"))
    assert observed == [response["X-Request-ID"]] * 2
    assert current_request_id.get() == "-"


@pytest.mark.django_db
def test_admin_lockout_logs_share_response_request_id(client):
    """Link real authentication lockout to the rate-limit HTTP event."""
    user = User.objects.create_user(
        username="trace.member", email="trace.member@example.test",
        password="correct-password", is_staff=True,
    )
    records = []

    class CapturingHandler(logging.Handler):
        """Collect audit messages with request ID enrichment."""

        def emit(self, record):
            records.append(record)

    handler = CapturingHandler()
    handler.addFilter(RequestIdFilter())
    audit_logger = logging.getLogger("aether.audit")
    http_logger = logging.getLogger("aether.http")
    audit_logger.addHandler(handler)
    http_logger.addHandler(handler)
    try:
        for _ in range(3):
            response = client.post(
                reverse("admin:login"),
                {"username": user.username, "password": "wrong-password"},
                REMOTE_ADDR="192.0.2.70",
            )
    finally:
        audit_logger.removeHandler(handler)
        http_logger.removeHandler(handler)
        handler.close()
    assert response.status_code == 429
    assert response["X-Request-ID"]
    lockout = [
        record
        for record in records
        if record.getMessage().startswith("authentication.lockout ")
    ]
    rate_limited_responses = [
        record
        for record in records
        if record.getMessage().startswith("http.response ")
        and "status_code=429" in record.getMessage()
    ]
    assert len(lockout) == len(rate_limited_responses) == 1
    assert lockout[0].request_id == response["X-Request-ID"]
    assert rate_limited_responses[0].request_id == response["X-Request-ID"]


def test_request_id_middleware_precedes_security_middleware():
    """Set correlation ID before other request middleware."""
    assert settings.MIDDLEWARE[0] == (
        "infrastructure.request_id.request_id_middleware"
    )
