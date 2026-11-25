"""Management command to auto-escalate overdue open reports."""
from django.core.management.base import BaseCommand
from reports.services import escalate_overdue_reports


class Command(BaseCommand):
    help = "Escalate open reports past their SLA due date."

    def handle(self, *args, **options):
        count = escalate_overdue_reports()
        self.stdout.write(self.style.SUCCESS(f"Escalated {count} overdue report(s)."))
