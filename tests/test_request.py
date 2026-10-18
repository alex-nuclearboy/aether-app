
"""Tests for shared HTTP request utilities."""

import pytest
from django.test import RequestFactory, override_settings

from infrastructure.request import _normalise_ip, get_client_ip


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("192.0.2.10", "192.0.2.10"),
        (" 192.0.2.10 ", "192.0.2.10"),
        ("2001:0db8:0000:0000::1", "2001:db8::1"),
        ("::ffff:192.0.2.10", "192.0.2.10"),
        ("invalid-ip", None),
        ("192.0.2.999", None),
        ("", None),
        ("   ", None),
        (None, None),
    ],
)
def test_normalise_ip(value, expected):
    """Normalise valid IP addresses and reject invalid values."""
    assert _normalise_ip(value) == expected


@pytest.mark.parametrize("environment", ["development", "test"])
@override_settings(
    CLIENT_IP_META_PRECEDENCE_ORDER=("REMOTE_ADDR",),
    CLIENT_IP_PROXY_ORDER="left-most",
    CLIENT_IP_PROXY_COUNT=None,
    CLIENT_IP_PROXY_TRUSTED_IPS=None,
)
def test_non_production_ignores_forwarded_headers(environment):
    """Use REMOTE_ADDR outside production."""
    request = RequestFactory().get(
        "/",
        REMOTE_ADDR="192.0.2.10",
        HTTP_X_FORWARDED_FOR="198.51.100.20",
        HTTP_X_REAL_IP="203.0.113.30",
    )

    with override_settings(ENVIRONMENT=environment):
        assert get_client_ip(request) == "192.0.2.10"


@override_settings(
    ENVIRONMENT="test",
    CLIENT_IP_META_PRECEDENCE_ORDER=("REMOTE_ADDR",),
    CLIENT_IP_PROXY_ORDER="left-most",
    CLIENT_IP_PROXY_COUNT=None,
    CLIENT_IP_PROXY_TRUSTED_IPS=None,
)
def test_get_client_ip_handles_invalid_remote_address():
    """Return None when REMOTE_ADDR is invalid."""
    request = RequestFactory().get(
        "/",
        REMOTE_ADDR="not-an-ip",
    )

    assert get_client_ip(request) is None


@override_settings(
    ENVIRONMENT="test",
    CLIENT_IP_META_PRECEDENCE_ORDER=("REMOTE_ADDR",),
    CLIENT_IP_PROXY_ORDER="left-most",
    CLIENT_IP_PROXY_COUNT=None,
    CLIENT_IP_PROXY_TRUSTED_IPS=None,
)
def test_get_client_ip_handles_missing_remote_address():
    """Return None when REMOTE_ADDR is missing."""
    request = RequestFactory().get("/")
    request.META.pop("REMOTE_ADDR", None)

    assert get_client_ip(request) is None


@override_settings(ENVIRONMENT="production")
def test_production_uses_last_forwarded_ip():
    """Use the address appended by the trusted Koyeb ingress."""
    request = RequestFactory().get(
        "/",
        REMOTE_ADDR="10.0.0.5",
        HTTP_X_FORWARDED_FOR="198.51.100.10, 203.0.113.25",
    )

    assert get_client_ip(request) == "203.0.113.25"


@override_settings(ENVIRONMENT="production")
def test_production_ignores_spoofed_forwarded_prefix():
    """Changing an untrusted prefix must not change the resolved IP."""
    factory = RequestFactory()

    first = factory.get(
        "/",
        REMOTE_ADDR="10.0.0.5",
        HTTP_X_FORWARDED_FOR="192.0.2.10, 203.0.113.25",
    )

    second = factory.get(
        "/",
        REMOTE_ADDR="10.0.0.5",
        HTTP_X_FORWARDED_FOR="198.51.100.20, 203.0.113.25",
    )

    assert get_client_ip(first) == "203.0.113.25"
    assert get_client_ip(second) == "203.0.113.25"


@override_settings(ENVIRONMENT="production")
def test_production_normalises_forwarded_ipv6():
    """Normalise the last IPv6 address in the forwarded chain."""
    request = RequestFactory().get(
        "/",
        REMOTE_ADDR="10.0.0.5",
        HTTP_X_FORWARDED_FOR=(
            "192.0.2.10, 2001:0db8:0000:0000::1"
        ),
    )

    assert get_client_ip(request) == "2001:db8::1"


@override_settings(ENVIRONMENT="production")
def test_production_rejects_invalid_last_forwarded_ip():
    """Never fall back to an earlier untrusted forwarded address."""
    request = RequestFactory().get(
        "/",
        REMOTE_ADDR="10.0.0.5",
        HTTP_X_FORWARDED_FOR="192.0.2.10, invalid-ip",
    )

    assert get_client_ip(request) is None


@override_settings(ENVIRONMENT="production")
def test_production_falls_back_to_remote_addr():
    """Use the direct peer address when X-Forwarded-For is absent."""
    request = RequestFactory().get(
        "/",
        REMOTE_ADDR="192.0.2.10",
    )

    assert get_client_ip(request) == "192.0.2.10"


@override_settings(
    ENVIRONMENT="development",
    CLIENT_IP_META_PRECEDENCE_ORDER=("REMOTE_ADDR",),
    CLIENT_IP_PROXY_ORDER="left-most",
    CLIENT_IP_PROXY_COUNT=None,
    CLIENT_IP_PROXY_TRUSTED_IPS=None,
)
def test_get_client_ip_passes_proxy_configuration(monkeypatch):
    """Pass the configured proxy policy to django-ipware."""
    captured = {}

    def fake_resolve_client_ip(request, **kwargs):
        captured.update(kwargs)
        return request.META["REMOTE_ADDR"], False

    monkeypatch.setattr(
        "infrastructure.request.resolve_client_ip",
        fake_resolve_client_ip,
    )

    request = RequestFactory().get(
        "/",
        REMOTE_ADDR="192.0.2.10",
    )

    assert get_client_ip(request) == "192.0.2.10"

    assert captured == {
        "proxy_order": "left-most",
        "proxy_count": None,
        "proxy_trusted_ips": None,
        "request_header_order": ("REMOTE_ADDR",),
    }
