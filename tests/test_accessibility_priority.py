"""Tests for STEP 14: Accessibility-aware priority, load_pois, recalc_priority, and dashboard score."""

import pytest
from django.core.management import call_command
from django.urls import reverse

from core.models import Category, POI, Ward
from reports.models import Report
from reports.services import accessibility_score, compute_priority, nearby_pois, ward_scores


@pytest.mark.django_db
def test_identical_report_near_school_has_higher_priority():
    ward = Ward.objects.create(name="Koramangala", zone="ZoneA", centroid_lat=12.9352, centroid_lon=77.6245)
    cat = Category.objects.create(name="Broken Pavement", sla_days=14, base_severity=3)

    # School at 12.9355, 77.6248
    POI.objects.create(name="Test School", poi_type=POI.Type.SCHOOL, lat=12.9355, lon=77.6248)

    # Report ~110 m away from school (within 300 m)
    near_report = Report.objects.create(
        category=cat,
        lat=12.9365,
        lon=77.6248,
        ward=ward,
        severity=2,
        affects_wheelchair=True,
    )
    # Identical report ~2.2 km away (outside 300 m)
    far_report = Report.objects.create(
        category=cat,
        lat=12.9555,
        lon=77.6248,
        ward=ward,
        severity=2,
        affects_wheelchair=True,
    )

    near_score = compute_priority(near_report)
    far_score = compute_priority(far_report)

    assert near_score == far_score + 15.0
    assert near_score > far_score


@pytest.mark.django_db
def test_load_pois_idempotent():
    call_command("load_pois")
    first_count = POI.objects.count()
    assert first_count >= 25

    # Running twice should not duplicate rows
    call_command("load_pois")
    assert POI.objects.count() == first_count


@pytest.mark.django_db
def test_recalc_priority_command_updates_open_reports():
    ward = Ward.objects.create(name="Indiranagar", zone="ZoneA", centroid_lat=12.9784, centroid_lon=77.6408)
    cat = Category.objects.create(name="Garbage Dumping", sla_days=3, base_severity=2)
    POI.objects.create(name="Indiranagar Hospital", poi_type=POI.Type.HOSPITAL, lat=12.9784, lon=77.6408)

    report = Report.objects.create(
        category=cat,
        lat=12.9785,
        lon=77.6408,
        ward=ward,
        severity=2,
        priority_score=0,
        status=Report.Status.SUBMITTED,
    )
    call_command("recalc_priority")
    report.refresh_from_db()
    # severity*10 (20) + hospital within 300m (15) = 35
    assert report.priority_score == 35.0


@pytest.mark.django_db
def test_accessibility_score_and_dashboard(client):
    w1 = Ward.objects.create(name="Ward One", zone="Z1", centroid_lat=12.93, centroid_lon=77.62)
    w2 = Ward.objects.create(name="Ward Two", zone="Z1", centroid_lat=12.97, centroid_lon=77.64)
    cat = Category.objects.create(name="Illegal Parking", sla_days=2, base_severity=1)

    # When max is 0, accessibility_score is 100
    assert accessibility_score(w1) == 100.0
    assert accessibility_score(w2) == 100.0

    # Add open report to w1 (priority 40) and w2 (priority 10)
    Report.objects.create(category=cat, lat=12.93, lon=77.62, ward=w1, priority_score=40.0, status=Report.Status.SUBMITTED)
    Report.objects.create(category=cat, lat=12.97, lon=77.64, ward=w2, priority_score=10.0, status=Report.Status.SUBMITTED)

    assert accessibility_score(w1) == 0.0
    assert accessibility_score(w2) == 75.0

    scores = {row["ward_name"]: row for row in ward_scores()}
    assert scores["Ward One"]["accessibility"] == 0.0
    assert scores["Ward Two"]["accessibility"] == 75.0

    resp = client.get(reverse("dashboard_home"))
    assert resp.status_code == 200
    assert b"Accessibility" in resp.content
    assert b"75.0%" in resp.content


@pytest.mark.django_db
def test_detail_page_shows_affected_chips_and_nearby_poi(client):
    ward = Ward.objects.create(name="Jayanagar", zone="ZoneB", centroid_lat=12.9308, centroid_lon=77.5838)
    cat = Category.objects.create(name="Vendor Encroachment", sla_days=5, base_severity=2)
    POI.objects.create(name="National High School", poi_type=POI.Type.SCHOOL, lat=12.9319, lon=77.5838)

    report = Report.objects.create(
        category=cat,
        lat=12.9308,
        lon=77.5838,
        ward=ward,
        severity=2,
        affects_wheelchair=True,
        affects_elderly=True,
    )
    report.priority_score = compute_priority(report)
    report.save()

    pois = nearby_pois(report, max_distance_m=300)
    assert len(pois) == 1
    assert pois[0]["poi_type"] == POI.Type.SCHOOL
    assert 100 <= pois[0]["distance_m"] <= 150

    resp = client.get(reverse("report_detail", args=[report.pk]))
    assert resp.status_code == 200
    content = resp.content.decode("utf-8")
    assert "Wheelchair" in content
    assert "Elderly" in content
    assert "Near: school (" in content
    assert "National High School" in content
