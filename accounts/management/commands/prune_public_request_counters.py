"""Delete expired public request counters in manageable batches."""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from accounts.models import PublicRequestCounter


class Command(BaseCommand):
    """Remove counter rows after the end of their fixed UTC window."""

    help = "Remove expired public request-limit counters."

    def add_arguments(self, parser):
        """Accept a batch size and an optional inspection-only mode."""
        parser.add_argument(
            "--batch-size",
            type=int,
            default=1000,
            help="Maximum number of expired counters per deletion batch.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Count expired counters without deleting them.",
        )

    def handle(self, *_args, **options):
        """Prune only rows expired at the start of this execution."""
        batch_size = options["batch_size"]
        if batch_size < 1:
            raise CommandError("--batch-size must be a positive integer.")

        cutoff = timezone.now()
        expired = PublicRequestCounter.objects.filter(
            expires_at__lte=cutoff
        )
        if options["dry_run"]:
            self.stdout.write(
                f"{expired.count()} expired public request counters "
                "would be removed."
            )
            return

        removed = 0
        while True:
            keys = list(
                expired.order_by("expires_at", "key")
                .values_list("key", flat=True)[:batch_size]
            )
            if not keys:
                break
            count, _ = PublicRequestCounter.objects.filter(
                key__in=keys,
                expires_at__lte=cutoff,
            ).delete()
            removed += count

        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {removed} expired public request counters."
            )
        )
