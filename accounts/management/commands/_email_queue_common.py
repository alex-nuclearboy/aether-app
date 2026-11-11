"""Shared management-command behaviour for independent email queues."""

from django.core.management.base import CommandError
from django.db import close_old_connections

from accounts.email_worker import validate_public_origin


class EmailQueueMixin:
    """Provide consistent polling and safe error handling for queues."""

    error_message = ""
    error_event = ""
    stopped_message = ""

    def add_arguments(self, parser):
        """Accept one-shot operation, a trusted origin and poll interval."""
        parser.add_argument(
            "--public-origin",
            required=True,
            help="Public website origin, including the HTTP(S) scheme.",
        )
        parser.add_argument(
            "--once",
            action="store_true",
            help="Process at most one queued email and exit.",
        )
        parser.add_argument(
            "--poll-seconds",
            type=float,
            default=5,
            help="Idle interval in seconds (default: 5).",
        )

    def run_worker(self, options, process_one, pause, log_error, write_output):
        """Poll work and recover without exposing sensitive exceptions."""
        interval = options["poll_seconds"]
        if not 0 < interval <= 300:
            raise CommandError("--poll-seconds must be between 0 and 300.")
        try:
            origin = validate_public_origin(options["public_origin"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        try:
            while True:
                try:
                    close_old_connections()
                    try:
                        outcome = process_one(origin)
                    finally:
                        close_old_connections()
                # A leased job can recover after its current lease expires.
                except Exception as exc:  # pylint: disable=W0718
                    if options["once"]:
                        raise CommandError(self.error_message) from None
                    log_error(
                        f"{self.error_event} error_type=%s",
                        type(exc).__name__,
                    )
                    pause(max(interval, 5.0))
                    continue

                if options["once"]:
                    write_output(f"Delivery outcome: {outcome or 'idle'}")
                    break
                if outcome is None:
                    pause(interval)
        except KeyboardInterrupt:
            write_output(self.stopped_message)
