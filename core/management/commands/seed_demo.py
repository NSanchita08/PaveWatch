# -*- coding: utf-8 -*-
"""Management command to seed demo data for PaveWatch.

Idempotent: running multiple times will not duplicate existing wards,
categories, users, POIs, or reports.
"""

import io
import random
from datetime import timedelta
from pathlib import Path

from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from django.utils import timezone
from django.contrib.auth import get_user_model

from core.models import Ward, Category, POI
from reports.demo_images import create_demo_photo
from reports.models import Report, ReportPhoto, StatusHistory
from reports.services import change_status
from django.db import transaction

User = get_user_model()

def _placeholder_image(category_name: str, kind: str, index: int) -> ContentFile:
    return create_demo_photo(category_name=category_name, kind=kind, index=index)

class Command(BaseCommand):
    help = "Seed demo data (wards, categories, users, POIs, reports)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--refresh-images",
            action="store_true",
            help="Regenerate all existing demo photos with realistic footpath obstruction illustrations",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting demo data seed..."))
        if options.get("refresh_images"):
            self._refresh_images()
            self.stdout.write(self.style.SUCCESS("Demo images refreshed successfully."))
            return
        self._seed_wards()
        self._seed_categories()
        self._seed_users()
        self._seed_pois()
        self._seed_reports()
        self.stdout.write(self.style.SUCCESS("Demo data seeded successfully."))

    def _refresh_images(self):
        """Regenerate all ReportPhoto images with realistic designs."""
        photos = ReportPhoto.objects.select_related("report__category")
        self.stdout.write(f"Refreshing {photos.count()} demo report photos...")
        for p in photos:
            cat_name = p.report.category.name if (p.report and p.report.category) else "Others"
            new_file = create_demo_photo(cat_name, p.kind, p.report.id)
            p.image.save(new_file.name, new_file, save=True)

    def _seed_wards(self):
        wards = [
            ("Koramangala", 12.9352, 77.6245, "ZoneA"),
            ("Indiranagar", 12.9784, 77.6408, "ZoneA"),
            ("Jayanagar", 12.9308, 77.5838, "ZoneB"),
            ("Malleshwaram", 13.0035, 77.5646, "ZoneB"),
            ("Whitefield", 12.9698, 77.7500, "ZoneC"),
            ("Yelahanka", 13.1007, 77.5963, "ZoneC"),
        ]
        for name, lat, lon, zone in wards:
            obj, created = Ward.objects.get_or_create(name=name, defaults={"zone": zone, "centroid_lat": lat, "centroid_lon": lon})
            if created:
                self.stdout.write(f"Created ward {name}")
            else:
                # Update centroid/zone if missing
                updated = False
                if obj.zone != zone:
                    obj.zone = zone
                    updated = True
                if obj.centroid_lat != lat or obj.centroid_lon != lon:
                    obj.centroid_lat = lat
                    obj.centroid_lon = lon
                    updated = True
                if updated:
                    obj.save()

    def _seed_categories(self):
        categories = [
            ("Illegal Parking", 2, 1),
            ("Garbage Dumping", 3, 2),
            ("Vendor Encroachment", 5, 2),
            ("Construction Debris", 7, 2),
            ("Others", 7, 1),
            ("Broken Pavement", 14, 3),
        ]
        for name, sla, severity in categories:
            obj, created = Category.objects.get_or_create(name=name, defaults={"sla_days": sla, "base_severity": severity})
            if created:
                self.stdout.write(f"Created category {name}")

    def _seed_users(self):
        # Admin
        admin, created = User.objects.get_or_create(username="admin1", defaults={"email": "admin1@example.com", "role": User.Role.ADMIN, "is_staff": True, "is_superuser": True})
        if created:
            admin.set_password("demo12345")
            admin.save()
            self.stdout.write("Created admin user admin1")
        # Supervisor
        sup, created = User.objects.get_or_create(username="supervisor1", defaults={"email": "supervisor1@example.com", "role": User.Role.SUPERVISOR, "zone": "ZoneA"})
        if created:
            sup.set_password("demo12345")
            sup.save()
            self.stdout.write("Created supervisor supervisor1")
        # Citizens
        for i in range(1, 3):
            username = f"citizen{i}"
            citizen, created = User.objects.get_or_create(username=username, defaults={"email": f"{username}@example.com", "role": User.Role.CITIZEN})
            if created:
                citizen.set_password("demo12345")
                citizen.save()
                self.stdout.write(f"Created citizen {username}")
        # Officers per ward
        for ward in Ward.objects.all():
            username = f"officer_{ward.name.lower().replace(' ', '_')}"
            officer, created = User.objects.get_or_create(username=username, defaults={"email": f"{username}@example.com", "role": User.Role.OFFICER, "ward": ward, "zone": ward.zone})
            if created:
                officer.set_password("demo12345")
                officer.save()
                self.stdout.write(f"Created officer {username} for ward {ward.name}")

    def _seed_pois(self):
        poi_types = [
            (POI.Type.SCHOOL, "School"),
            (POI.Type.HOSPITAL, "Hospital"),
            (POI.Type.BUS_STOP, "Bus stop"),
            (POI.Type.METRO, "Metro station"),
        ]
        existing = POI.objects.count()
        target = 30
        if existing >= target:
            self.stdout.write("POIs already seeded.")
            return
        while POI.objects.count() < target:
            ward = random.choice(list(Ward.objects.all()))
            lat_offset = random.uniform(-0.01, 0.01)
            lon_offset = random.uniform(-0.01, 0.01)
            lat = ward.centroid_lat + lat_offset
            lon = ward.centroid_lon + lon_offset
            ptype_code, ptype_name = random.choice(poi_types)
            name = f"{ptype_name} {random.randint(1, 999)}"
            POI.objects.get_or_create(name=name, poi_type=ptype_code, lat=lat, lon=lon)
        self.stdout.write(f"Seeded {POI.objects.count()} POIs.")

    def _seed_reports(self):
        # If there are already reports, skip to keep idempotent.
        if Report.objects.exists():
            self.stdout.write("Reports already exist, skipping report generation.")
            return
        citizens = list(User.objects.filter(role=User.Role.CITIZEN))
        categories = list(Category.objects.all())
        statuses = [Report.Status.SUBMITTED, Report.Status.ACKNOWLEDGED, Report.Status.IN_PROGRESS, Report.Status.RESOLVED, Report.Status.CLOSED, Report.Status.REOPENED]
        now = timezone.now()
        for i in range(60):
            reporter = random.choice(citizens)
            category = random.choice(categories)
            ward = random.choice(list(Ward.objects.all()))
            # Random location near ward centroid
            lat = ward.centroid_lat + random.uniform(-0.02, 0.02)
            lon = ward.centroid_lon + random.uniform(-0.02, 0.02)
            severity = random.randint(1, 3)
            # Random creation time within last 8 weeks
            created_at = now - timedelta(days=random.randint(0, 56), minutes=random.randint(0, 1440))
            # Initial status
            status = random.choice(statuses)
            report = Report.objects.create(
                reporter=reporter,
                category=category,
                lat=lat,
                lon=lon,
                ward=ward,
                severity=severity,
                description=f"Demo report {i+1}",
                status=status,
                created_at=created_at,
            )
            # Set tracking_id after save to have pk
            report.tracking_id = f"PW-{created_at.year}-{report.pk:06d}"
            report.sla_due_at = created_at + timedelta(days=category.sla_days)
            report.save(update_fields=["tracking_id", "sla_due_at"])
            # Add a BEFORE photo
            img_file = _placeholder_image(category.name, ReportPhoto.Kind.BEFORE, i + 1)
            ReportPhoto.objects.create(report=report, image=img_file, kind=ReportPhoto.Kind.BEFORE, uploaded_by=reporter)
            # Optional AFTER photo for RESOLVED status
            if status == Report.Status.RESOLVED:
                img_file_af = _placeholder_image(category.name, ReportPhoto.Kind.AFTER, i + 1)
                ReportPhoto.objects.create(report=report, image=img_file_af, kind=ReportPhoto.Kind.AFTER, uploaded_by=random.choice(User.objects.filter(role=User.Role.OFFICER)))
            # Status history entry
            StatusHistory.objects.create(report=report, from_status="", to_status=status, changed_by=reporter, remark="Seeded status")
            # Random escalation flag for overdue reports
            if status in Report.OPEN_STATUSES and report.sla_due_at < now:
                report.escalated = True
                report.save(update_fields=["escalated"])
        self.stdout.write(f"Created {Report.objects.count()} demo reports.")
