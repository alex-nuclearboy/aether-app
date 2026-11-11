"""Process queued verification emails in an independent worker process."""

import logging
from time import sleep

from django.core.management.base import BaseCommand

from accounts.email_worker import deliver_next_verification_email
from accounts.management.commands._email_queue_common import (
    EmailQueueMixin,
)

logger = logging.getLogger("aether.email_worker")


class Command(EmailQueueMixin, BaseCommand):
    """Drain PostgreSQL verification jobs without SMTP in HTTP."""

    help = "Process queued verification emails using a trusted public origin."
    error_message = "Verification email processing failed."
    error_event = "verification_email.worker_iteration_failed"
    stopped_message = "Verification email worker stopped."

    def handle(self, *_args, **options):
        """Run the queue with the existing verification delivery service."""
        self.run_worker(
            options, deliver_next_verification_email, sleep, logger.error,
            self.stdout.write,
        )
