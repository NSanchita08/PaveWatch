"""Management command to auto-close stale RESOLVED reports without citizen feedback."""
from django.core.management.base import BaseCommand
from reports.services import auto_close_resolved_reports


class Command(BaseCommand):
    help = "Auto-close RESOLVED reports older than AUTO_CLOSE_DAYS with no citizen feedback."

    def handle(self, *args, **options):
        count = auto_close_resolved_reports()
        self.stdout.write(self.style.SUCCESS(f"Auto-closed {count} resolved report(s)."))
