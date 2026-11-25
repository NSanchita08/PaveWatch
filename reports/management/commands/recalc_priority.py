"""Management command to recalculate priority_score on reports."""

from django.core.management.base import BaseCommand

from reports.services import recalc_all_priorities


class Command(BaseCommand):
    help = "Recalculate accessibility-aware priority_score for open reports (or all with --all)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--all",
            action="store_true",
            help="Recalculate priority_score for all reports, including closed/rejected.",
        )

    def handle(self, *args, **options):
        include_closed = bool(options.get("all"))
        updated = recalc_all_priorities(include_closed=include_closed)
        scope = "all" if include_closed else "open"
        self.stdout.write(
            self.style.SUCCESS(f"Recalculated priorities ({scope} reports): {updated} updated.")
        )
