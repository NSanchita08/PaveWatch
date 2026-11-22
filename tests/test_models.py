import pytest
from django.urls import reverse
from core.models import Ward, Category, POI
from accounts.models import User
from reports.models import Report, ReportPhoto, StatusHistory, Confirmation, Notification

@pytest.mark.django_db
def test_superuser_gets_admin_role():
    admin_user = User.objects.create_superuser(
        username="admin_test",
        email="admin@test.com",
        password="password123"
    )
    assert admin_user.is_superuser
    assert admin_user.role == User.Role.ADMIN

@pytest.mark.django_db
def test_create_ward_category_poi():
    ward = Ward.objects.create(
        name="Koramangala",
        zone="South",
        centroid_lat=12.9352,
        centroid_lon=77.6245
    )
    assert str(ward) == "Koramangala"

    category = Category.objects.create(
        name="Illegal Parking",
        sla_days=2,
        base_severity=2
    )
    assert str(category) == "Illegal Parking"

    poi = POI.objects.create(
        name="National Public School",
        poi_type=POI.Type.SCHOOL,
        lat=12.9360,
        lon=77.6250
    )
    assert poi.poi_type == "school"

@pytest.mark.django_db
def test_create_report_and_related_models():
    ward = Ward.objects.create(name="Indiranagar", zone="East", centroid_lat=12.9784, centroid_lon=77.6408)
    category = Category.objects.create(name="Broken Pavement", sla_days=14, base_severity=3)
    user = User.objects.create_user(username="citizen_test", password="password123")

    report = Report.objects.create(
        tracking_id="PW-2026-000001",
        reporter=user,
        category=category,
        description="Cracked slab on footpath",
        landmark="Near Metro Station",
        lat=12.9785,
        lon=77.6410,
        ward=ward,
        severity=3,
        status=Report.Status.SUBMITTED,
        priority_score=35.0,
        trust_score=50
    )
    assert report.pk is not None
    assert str(report) == "PW-2026-000001"

    history = StatusHistory.objects.create(
        report=report,
        from_status="",
        to_status=Report.Status.SUBMITTED,
        changed_by=user,
        remark="Initial report"
    )
    assert history.to_status == "SUBMITTED"

    confirmation = Confirmation.objects.create(
        report=report,
        user=user,
        kind=Confirmation.Kind.STILL_THERE
    )
    assert confirmation.kind == "STILL_THERE"

    notification = Notification.objects.create(
        user=user,
        report=report,
        message="Your report has been received."
    )
    assert notification.is_read is False

@pytest.mark.django_db
def test_admin_can_create_ward_category_report(client):
    admin_user = User.objects.create_superuser(
        username="admin_client",
        email="admin_client@test.com",
        password="password123"
    )
    client.force_login(admin_user)

    # 1. Create Ward via Admin
    ward_add_url = reverse("admin:core_ward_add")
    response = client.post(ward_add_url, {
        "name": "Jayanagar",
        "zone": "South",
        "centroid_lat": 12.9308,
        "centroid_lon": 77.5838,
    })
    assert response.status_code == 302
    ward = Ward.objects.get(name="Jayanagar")

    # 2. Create Category via Admin
    cat_add_url = reverse("admin:core_category_add")
    response = client.post(cat_add_url, {
        "name": "Garbage Dumping",
        "sla_days": 3,
        "base_severity": 2,
    })
    assert response.status_code == 302
    category = Category.objects.get(name="Garbage Dumping")

    # 3. Create Report via Admin
    report_add_url = reverse("admin:reports_report_add")
    response = client.post(report_add_url, {
        "tracking_id": "PW-2026-000002",
        "reporter": admin_user.pk,
        "category": category.pk,
        "description": "Garbage pile blocking pedestrian walkway",
        "landmark": "Near 4th Block Complex",
        "lat": 12.9310,
        "lon": 77.5840,
        "ward": ward.pk,
        "severity": 2,
        "status": Report.Status.SUBMITTED,
        "priority_score": 20.0,
        "trust_score": 30,
        # Inlines management form fields
        "photos-TOTAL_FORMS": 0,
        "photos-INITIAL_FORMS": 0,
        "photos-MIN_NUM_FORMS": 0,
        "photos-MAX_NUM_FORMS": 1000,
        "history-TOTAL_FORMS": 0,
        "history-INITIAL_FORMS": 0,
        "history-MIN_NUM_FORMS": 0,
        "history-MAX_NUM_FORMS": 1000,
    })
    assert response.status_code == 302
    assert Report.objects.filter(tracking_id="PW-2026-000002").exists()
