"""Management command to load POIs from data/pois.json (idempotent upsert)."""

import json
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from core.models import POI


class Command(BaseCommand):
    help = "Load and upsert Points of Interest (POIs) from data/pois.json."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default=str(Path(settings.BASE_DIR) / "data" / "pois.json"),
            help="Path to the POIs JSON file (default: data/pois.json).",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])
        if not file_path.exists():
            raise CommandError(f"POI data file not found: {file_path}")

        with file_path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)

        if not isinstance(data, list):
            raise CommandError("POIs JSON must be a list of objects.")

        valid_types = {choice for choice, _ in POI.Type.choices}
        created_count = 0
        updated_count = 0

        for idx, item in enumerate(data):
            name = (item.get("name") or "").strip()
            poi_type = (item.get("type") or "").strip()
            lat = item.get("lat")
            lon = item.get("lon")

            if poi_type not in valid_types:
                raise CommandError(f"Invalid POI type '{poi_type}' at index {idx}.")
            if lat is None or lon is None:
                raise CommandError(f"Missing lat/lon at index {idx}.")

            _, created = POI.objects.update_or_create(
                name=name,
                poi_type=poi_type,
                defaults={"lat": float(lat), "lon": float(lon)},
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Loaded POIs from {file_path.name}: {created_count} created, {updated_count} updated."
            )
        )
