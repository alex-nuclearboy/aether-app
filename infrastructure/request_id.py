"""Request-scoped correlation IDs for HTTP and logging."""

import logging
from contextvars import ContextVar
from inspect import iscoroutinefunction
from uuid import uuid4

from django.utils.decorators import sync_and_async_middleware


current_request_id = ContextVar("aether_request_id", default="-")
http_logger = logging.getLogger("aether.http")


# pylint: disable=too-few-public-methods
class RequestIdFilter(logging.Filter):
    """Enrich log records with a request-scoped ID."""

    def filter(self, record):
        record.request_id = current_request_id.get()
        return True


def _finish(request, response):
    """Attach correlation header and log rate-limited responses."""
    response["X-Request-ID"] = request.request_id

    if response.status_code >= 500:
        log_level = logging.ERROR
    elif response.status_code == 429:
        log_level = logging.WARNING
    else:
        log_level = logging.INFO

    http_logger.log(
        log_level,
        "http.response method=%s path=%s status_code=%s",
        request.method,
        request.path,
        response.status_code,
    )

    return response


@sync_and_async_middleware
def request_id_middleware(get_response):
    """Generate and isolate request IDs in sync and async execution."""
    if iscoroutinefunction(get_response):

        async def middleware(request):
            request.request_id = uuid4().hex
            token = current_request_id.set(request.request_id)
            try:
                return _finish(request, await get_response(request))
            finally:
                current_request_id.reset(token)

    else:

        def middleware(request):
            request.request_id = uuid4().hex
            token = current_request_id.set(request.request_id)
            try:
                return _finish(request, get_response(request))
            finally:
                current_request_id.reset(token)

    return middleware
