"""Redact sensitive account confirmation URLs from configured log output."""

import logging
import re

from colorlog import ColoredFormatter


_VERIFICATION_PATH = re.compile(r"/email/verify/[^\s\"'<>\x1b]+")
_REDACTED_PATH = "/email/verify/<redacted>/"
_RESET_PATH = re.compile(r"/password/reset/confirm/[^\s\"'<>\x1b]+")
_RESET_REDACTED_PATH = "/password/reset/confirm/<redacted>/"


def redact_verification_paths(message: str) -> str:
    """Mask sensitive confirmation paths, including exception tracebacks."""
    message = _VERIFICATION_PATH.sub(_REDACTED_PATH, message)
    return _RESET_PATH.sub(_RESET_REDACTED_PATH, message)


# Formatter adapters intentionally implement only the formatting hook.
# pylint: disable=too-few-public-methods
class RedactingFormatter(logging.Formatter):
    """Redact confirmation URLs from fully formatted log output."""

    def format(self, record):
        return redact_verification_paths(super().format(record))


class RedactingColouredFormatter(ColoredFormatter):
    """Redact confirmation URLs while retaining coloured log output."""

    def format(self, record):
        return redact_verification_paths(super().format(record))
