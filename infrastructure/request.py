
"""Shared utilities for HTTP request metadata."""

from ipaddress import IPv6Address, ip_address

from django.conf import settings
from django.http import HttpRequest
from ipware import get_client_ip as resolve_client_ip


def _normalise_ip(value: str | None) -> str | None:
    """Validate and normalise an IPv4 or IPv6 address."""
    if not isinstance(value, str) or not value.strip():
        return None

    try:
        address = ip_address(value.strip())
    except ValueError:
        return None

    if isinstance(address, IPv6Address) and address.ipv4_mapped:
        address = address.ipv4_mapped

    return address.compressed


def get_client_ip(request: HttpRequest) -> str | None:
    """Resolve and normalise the client IP using the proxy policy."""
    if settings.ENVIRONMENT == "production":
        forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

        if isinstance(forwarded_for, str) and forwarded_for:
            return _normalise_ip(forwarded_for.rsplit(",", 1)[-1])

        return _normalise_ip(request.META.get("REMOTE_ADDR"))

    client_ip, _ = resolve_client_ip(
        request,
        proxy_order=settings.CLIENT_IP_PROXY_ORDER,
        proxy_count=settings.CLIENT_IP_PROXY_COUNT,
        proxy_trusted_ips=settings.CLIENT_IP_PROXY_TRUSTED_IPS,
        request_header_order=settings.CLIENT_IP_META_PRECEDENCE_ORDER,
    )

    return _normalise_ip(client_ip)
