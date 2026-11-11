"""Process password reset messages independently from HTTP requests."""

import logging
from time import sleep

from django.core.management.base import BaseCommand

from accounts.management.commands._email_queue_common import (
    EmailQueueMixin,
)
from accounts.password_reset_worker import deliver_next_password_reset_email

logger = logging.getLogger("aether.email_worker")


class Command(EmailQueueMixin, BaseCommand):
    """Process reset email jobs with bounded worker-error recovery."""

    help = "Process password reset email jobs using a trusted public origin."
    error_message = "Password reset email processing failed."
    error_event = "password_reset.worker_iteration_failed"
    stopped_message = "Password reset email worker stopped."

    def handle(self, *_args, **options):
        """Run the queue with the existing password-reset delivery service."""
        self.run_worker(
            options, deliver_next_password_reset_email, sleep, logger.error,
            self.stdout.write,
        )
