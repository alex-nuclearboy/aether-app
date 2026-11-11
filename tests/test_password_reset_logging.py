"""Safeguards for one-time password reset links in application logs."""

import logging
from unittest.mock import patch

import pytest
from django.http import HttpResponse

from config.logging import LoggingLevels, build_logging_config
from infrastructure.log_redaction import (
    RedactingColouredFormatter,
    RedactingFormatter,
    redact_verification_paths,
)
from infrastructure.request_id import request_id_middleware


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (
            "/password/reset/confirm/private-uid/private-token/",
            "/password/reset/confirm/<redacted>/",
        ),
        (
            "/password/reset/confirm/private-uid/private-token/extra/",
            "/password/reset/confirm/<redacted>/",
        ),
        ("/password/reset/done/", "/password/reset/done/"),
    ],
)
def test_password_reset_paths_masked_before_routing(rf, path, expected):
    """Mask unresolved or redirected reset links in aether.http output."""
    logged_paths = []

    def capture_log(_level, _format, _method, actual_path, _status):
        logged_paths.append(actual_path)

    with patch(
        "infrastructure.request_id.http_logger.log",
        side_effect=capture_log,
    ):
        response = request_id_middleware(
            lambda _request: HttpResponse(status=404)
        )(rf.get(path))

    assert response.status_code == 404
    assert logged_paths == [expected]
    assert all("private-token" not in item for item in logged_paths)


def test_reset_paths_masked_from_django_log_messages():
    """Sanitise fully formatted framework exceptions and access paths."""
    message = (
        "Not Found: /password/reset/confirm/private-uid/private-token/"
    )
    assert redact_verification_paths(message) == (
        "Not Found: /password/reset/confirm/<redacted>/"
    )
@pytest.mark.parametrize(
    ("url", "redacted"),
    [
        (
            "/email/verify/private-id/private-token/",
            "/email/verify/<redacted>/",
        ),
        (
            "/password/reset/confirm/private-id/private-token/",
            "/password/reset/confirm/<redacted>/",
        ),
    ],
)
@pytest.mark.parametrize(
    "formatter_class",
    [RedactingFormatter, RedactingColouredFormatter],
)
def test_sensitive_urls_are_redacted_after_formatting(
    formatter_class, url, redacted,
):
    """Keep email confirmation tokens out of Django diagnostic output."""
    formatter = formatter_class("%(name)s: %(message)s")
    record = logging.LogRecord(
        "django.request",
        logging.WARNING,
        __file__,
        1,
        "Not Found: %s",
        (url,),
        None,
    )
    message = formatter.format(record)
    assert "private-id" not in message
    assert "private-token" not in message
    assert redacted in message


@pytest.mark.parametrize("debug", [True, False])
def test_application_logging_uses_redacting_formatters(tmp_path, debug):
    """Protect both console and file handlers in project configuration."""
    config = build_logging_config(
        base_dir=tmp_path,
        debug=debug,
        levels=LoggingLevels(
            root="INFO", app="INFO", django="INFO",
            database="WARNING", audit="INFO",
        ),
    )
    assert config["formatters"]["plain"]["()"] == (
        "infrastructure.log_redaction.RedactingFormatter"
    )
    assert config["formatters"]["colour"]["()"] == (
        "infrastructure.log_redaction.RedactingColouredFormatter"
    )
