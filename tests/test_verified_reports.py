"""Tests for STEP 12: Verified reports (EXIF, duplicate detection, still-there confirmation, verified badge)."""
import pytest
from datetime import datetime, timedelta
from django.utils import timezone
from django.urls import reverse
from django.core.files.base import ContentFile

from accounts.models import User
from core.models import Ward, Category
from reports.models import Report, Confirmation
from reports.services import (
    create_report,
    find_duplicates,
    compute_trust,
    compute_priority,
    add_confirmation,
)


@pytest.fixture
def ward(db):
    return Ward.objects.create(
        name="Koramangala", zone="South", centroid_lat=12.9352, centroid_lon=77.6245
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Broken Pavement", sla_days=7, base_severity=2)


@pytest.fixture
def citizen(db, ward):
    return User.objects.create_user(
        username="test_citizen",
        email="citizen@example.com",
        password="password123",
        role=User.Role.CITIZEN,
        ward=ward,
    )


@pytest.fixture
def citizen2(db, ward):
    return User.objects.create_user(
        username="test_citizen2",
        email="citizen2@example.com",
        password="password123",
        role=User.Role.CITIZEN,
        ward=ward,
    )


@pytest.fixture
def officer(db, ward):
    return User.objects.create_user(
        username="test_officer",
        email="officer@example.com",
        password="password123",
        role=User.Role.OFFICER,
        ward=ward,
    )


@pytest.mark.django_db
def test_photo_without_exif_gives_lower_trust(citizen, category):
    """Photo without EXIF gives lower trust than photo with valid EXIF."""
    # 1. Report without EXIF
    no_exif_photo = ContentFile(b"fake-image-bytes", name="test1.jpg")
    r_no_exif = create_report(
        reporter=citizen,
        category=category,
        lat=12.9352,
        lon=77.6245,
        description="Pavement broken",
        landmark="Near post office",
        severity=2,
        affects={},
        processed_photos=[no_exif_photo],
        exif_results=[(None, None, None)],
    )

    assert r_no_exif.exif_ok is False
    assert r_no_exif.trust_score < 50
    assert r_no_exif.is_verified is False

    # 2. Report with matching GPS and fresh timestamp in EXIF
    valid_exif_photo = ContentFile(b"fake-image-bytes", name="test2.jpg")
    now_naive = timezone.now().replace(tzinfo=None) - timedelta(hours=2)
    r_with_exif = create_report(
        reporter=citizen,
        category=category,
        lat=12.9352,
        lon=77.6245,
        description="Pavement broken with valid photo",
        landmark="Near post office",
        severity=2,
        affects={},
        processed_photos=[valid_exif_photo],
        exif_results=[(12.93521, 77.62451, now_naive)],
    )

    assert r_with_exif.exif_ok is True
    assert r_with_exif.trust_score >= 50
    assert r_with_exif.is_verified is True
    assert r_with_exif.trust_score > r_no_exif.trust_score


@pytest.mark.django_db
def test_duplicate_detection_within_50m_and_200m(citizen, category):
    """Duplicate within 50 m of same category is found; one at 200 m is not."""
    base_lat = 12.9352
    base_lon = 77.6245

    # Create original open report
    r1 = create_report(
        reporter=citizen,
        category=category,
        lat=base_lat,
        lon=base_lon,
        description="Original open obstruction",
        landmark="Corner house",
        severity=2,
        affects={},
        processed_photos=[ContentFile(b"fake-img", name="img.jpg")],
        exif_results=[(None, None, None)],
    )

    # 1. Check point ~25 meters away (1 deg lat ~ 111,000 m -> 0.00022 deg ~ 24.4 m)
    near_lat = base_lat + 0.00022
    near_lon = base_lon
    dups_near = find_duplicates(near_lat, near_lon, category.id)
    assert len(dups_near) == 1
    assert dups_near[0].pk == r1.pk

    # 2. Check point ~200 meters away (0.0018 deg lat ~ 200 m)
    far_lat = base_lat + 0.0018
    far_lon = base_lon
    dups_far = find_duplicates(far_lat, far_lon, category.id)
    assert len(dups_far) == 0

    # 3. Check different category at 25 meters
    cat2 = Category.objects.create(name="Garbage Dumping", sla_days=3, base_severity=2)
    dups_diff_cat = find_duplicates(near_lat, near_lon, cat2.id)
    assert len(dups_diff_cat) == 0


@pytest.mark.django_db
def test_check_duplicates_api(client, citizen, category):
    """The /report/check-duplicates/ endpoint returns JSON and excludes reporter identity."""
    client.force_login(citizen)

    # Create base report
    r1 = create_report(
        reporter=citizen,
        category=category,
        lat=12.9352,
        lon=77.6245,
        description="Footpath blocked",
        landmark="Opposite bakery",
        severity=2,
        affects={},
        processed_photos=[ContentFile(b"img", name="img.jpg")],
        exif_results=[(None, None, None)],
    )

    # Query duplicates near r1
    url = reverse("check_duplicates")
    resp = client.get(url, {"lat": "12.9353", "lon": "77.6245", "category_id": str(category.id)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    dup_entry = data["duplicates"][0]
    assert dup_entry["id"] == r1.pk
    assert dup_entry["tracking_id"] == r1.tracking_id
    assert "reporter" not in dup_entry
    assert "citizen" not in str(data)  # Rule 14: no reporter username/email in JSON


@pytest.mark.django_db
def test_submit_anyway_sets_duplicate_of(citizen, category):
    """Submitting with force_duplicate_of sets the duplicate_of foreign key."""
    r_orig = create_report(
        reporter=citizen,
        category=category,
        lat=12.9352,
        lon=77.6245,
        description="First report",
        landmark="Lane 1",
        severity=2,
        affects={},
        processed_photos=[ContentFile(b"img", name="img1.jpg")],
        exif_results=[(None, None, None)],
    )

    r_dup = create_report(
        reporter=citizen,
        category=category,
        lat=12.9353,
        lon=77.6245,
        description="Second report (duplicate)",
        landmark="Lane 1",
        severity=2,
        affects={},
        processed_photos=[ContentFile(b"img", name="img2.jpg")],
        exif_results=[(None, None, None)],
        force_duplicate_of=r_orig,
    )

    assert r_dup.duplicate_of == r_orig
    assert r_orig.duplicates.count() == 1


@pytest.mark.django_db
def test_still_there_confirmation(client, citizen, citizen2, category):
    """Still there button increments priority and trust, with 1 confirmation per user."""
    report = create_report(
        reporter=citizen,
        category=category,
        lat=12.9352,
        lon=77.6245,
        description="Ongoing issue",
        landmark="Bus stop",
        severity=2,
        affects={},
        processed_photos=[ContentFile(b"img", name="img.jpg")],
        exif_results=[(None, None, None)],
    )

    initial_priority = report.priority_score
    initial_trust = report.trust_score

    # Citizen 2 confirms
    client.force_login(citizen2)
    url = reverse("report_confirm", args=[report.pk])
    resp = client.post(url, follow=True)
    assert resp.status_code == 200

    report.refresh_from_db()
    assert report.confirmations.filter(kind=Confirmation.Kind.STILL_THERE).count() == 1
    # compute_priority adds min(2 * confirmations, 10) => +2
    assert report.priority_score == initial_priority + 2
    # compute_trust adds min(5 * confirmations, 20) => +5
    assert report.trust_score == initial_trust + 5

    # Confirming again by the same user should not create duplicate or change score
    resp2 = client.post(url, follow=True)
    assert resp2.status_code == 200
    report.refresh_from_db()
    assert report.confirmations.filter(kind=Confirmation.Kind.STILL_THERE).count() == 1
    assert report.priority_score == initial_priority + 2


@pytest.mark.django_db
def test_verified_badge_displayed_on_views(client, citizen, officer, category):
    """Verified badge appears when trust_score >= 50 on detail and officer views."""
    # Report with trust_score >= 50 (valid EXIF)
    now_naive = timezone.now().replace(tzinfo=None) - timedelta(hours=1)
    r_verified = create_report(
        reporter=citizen,
        category=category,
        lat=12.9352,
        lon=77.6245,
        description="Verified broken pavement",
        landmark="Near metro",
        severity=2,
        affects={},
        processed_photos=[ContentFile(b"img", name="img.jpg")],
        exif_results=[(12.9352, 77.6245, now_naive)],
    )
    assert r_verified.trust_score >= 50

    # Detail view
    resp_detail = client.get(reverse("report_detail", args=[r_verified.pk]))
    assert resp_detail.status_code == 200
    assert "Verified Report" in resp_detail.content.decode()

    # Officer queue view
    client.force_login(officer)
    resp_queue = client.get(reverse("officer_queue"))
    assert resp_queue.status_code == 200
    assert "Verified" in resp_queue.content.decode()

    # Officer manage view
    resp_manage = client.get(reverse("officer_manage_report", args=[r_verified.pk]))
    assert resp_manage.status_code == 200
    assert "Verified" in resp_manage.content.decode()
