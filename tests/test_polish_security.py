"""Tests for STEP 17: Polish, 404, favicon, and daily report rate limit."""

import pytest
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.urls import reverse

from core.models import Category, Ward
from reports.services import create_report

User = get_user_model()


@pytest.mark.django_db
def test_daily_report_rate_limit_enforced(settings):
    settings.MAX_REPORTS_PER_DAY = 3
    Ward.objects.create(name="Koramangala", zone="ZoneA", centroid_lat=12.9352, centroid_lon=77.6245)
    cat = Category.objects.create(name="Illegal Parking", sla_days=2, base_severity=1)
    user = User.objects.create_user(username="spammer", password="pw", role=User.Role.CITIZEN)

    for i in range(3):
        create_report(
            reporter=user,
            category=cat,
            lat=12.9352,
            lon=77.6245,
            description=f"Report {i}",
            landmark="Main Rd",
            severity=1,
            affects={},
            processed_photos=[ContentFile(b"x", name=f"p{i}.jpg")],
            exif_results=[(None, None, None)],
        )

    with pytest.raises(ValueError, match="Daily report limit reached"):
        create_report(
            reporter=user,
            category=cat,
            lat=12.9352,
            lon=77.6245,
            description="Report 4",
            landmark="Main Rd",
            severity=1,
            affects={},
            processed_photos=[ContentFile(b"x", name="p4.jpg")],
            exif_results=[(None, None, None)],
        )


@pytest.mark.django_db
def test_home_has_favicon_and_404_renders(client, settings):
    settings.DEBUG = False
    settings.ALLOWED_HOSTS = ["testserver"]

    resp = client.get(reverse("home"))
    assert resp.status_code == 200
    assert b"favicon.svg" in resp.content

    resp_404 = client.get("/nonexistent-page-xyz/")
    assert resp_404.status_code == 404
    assert b"Page Not Found" in resp_404.content
