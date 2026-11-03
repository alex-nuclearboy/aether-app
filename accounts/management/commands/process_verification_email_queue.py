"""Process queued verification emails in an independent worker process."""

from time import sleep

from django.core.management.base import BaseCommand, CommandError
from django.db import close_old_connections

from accounts.email_worker import (
    deliver_next_verification_email,
    validate_public_origin,
)


class Command(BaseCommand):
    """Drain PostgreSQL verification jobs without running SMTP in HTTP."""

    help = "Process queued verification emails using a trusted public origin."

    def add_arguments(self, parser):
        """Require an explicit origin and accept a one-job test mode."""
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

    def handle(self, *_args, **options):
        """Consume jobs until stopped, closing stale database connections."""
        interval = options["poll_seconds"]
        if not 0 < interval <= 300:
            raise CommandError("--poll-seconds must be between 0 and 300.")

        try:
            origin = validate_public_origin(options["public_origin"])
        except ValueError as exc:
            raise CommandError(str(exc)) from exc

        try:
            while True:
                close_old_connections()
                try:
                    outcome = deliver_next_verification_email(origin)
                finally:
                    close_old_connections()

                if options["once"]:
                    self.stdout.write(f"Delivery outcome: {outcome or 'idle'}")
                    break
                if outcome is None:
                    sleep(interval)
        except KeyboardInterrupt:
            self.stdout.write("Verification email worker stopped.")
