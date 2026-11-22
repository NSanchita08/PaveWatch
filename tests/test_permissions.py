import pytest
from django.urls import reverse
from core.models import Ward, Category
from accounts.models import User
from reports.models import Report

@pytest.mark.django_db
def test_anonymous_redirected_to_login(client):
    response = client.get(reverse("officer_queue"))
    assert response.status_code == 302
    assert reverse("login") in response.url

@pytest.mark.django_db
def test_citizen_forbidden_on_officer_queue(client):
    citizen = User.objects.create_user(
        username="test_citizen",
        password="password123",
        role=User.Role.CITIZEN
    )
    client.force_login(citizen)
    response = client.get(reverse("officer_queue"))
    assert response.status_code == 403

@pytest.mark.django_db
def test_officer_ward_permissions(client):
    ward_a = Ward.objects.create(name="Ward A", zone="East", centroid_lat=12.97, centroid_lon=77.64)
    ward_b = Ward.objects.create(name="Ward B", zone="West", centroid_lat=12.93, centroid_lon=77.58)
    cat = Category.objects.create(name="Obstruction", sla_days=3, base_severity=2)

    officer_a = User.objects.create_user(
        username="officer_a",
        password="password123",
        role=User.Role.OFFICER,
        ward=ward_a,
        zone="East"
    )

    report_in_ward_a = Report.objects.create(
        tracking_id="PW-2026-000101",
        category=cat,
        ward=ward_a,
        lat=12.971,
        lon=77.641
    )
    report_in_ward_b = Report.objects.create(
        tracking_id="PW-2026-000102",
        category=cat,
        ward=ward_b,
        lat=12.931,
        lon=77.581
    )

    client.force_login(officer_a)

    # Allowed on Ward A
    resp_a = client.get(reverse("officer_manage_report", kwargs={"report_id": report_in_ward_a.pk}))
    assert resp_a.status_code == 200

    # Forbidden on Ward B
    resp_b = client.get(reverse("officer_manage_report", kwargs={"report_id": report_in_ward_b.pk}))
    assert resp_b.status_code == 403

@pytest.mark.django_db
def test_supervisor_and_admin_permissions(client):
    ward_east = Ward.objects.create(name="Ward East", zone="EastZone", centroid_lat=12.97, centroid_lon=77.64)
    ward_west = Ward.objects.create(name="Ward West", zone="WestZone", centroid_lat=12.93, centroid_lon=77.58)
    cat = Category.objects.create(name="Pothole", sla_days=7, base_severity=2)

    supervisor = User.objects.create_user(
        username="sup_east",
        password="password123",
        role=User.Role.SUPERVISOR,
        zone="EastZone"
    )
    admin_user = User.objects.create_superuser(
        username="super_admin",
        password="password123",
        email="admin@pavewatch.org"
    )

    report_east = Report.objects.create(category=cat, ward=ward_east, lat=12.97, lon=77.64)
    report_west = Report.objects.create(category=cat, ward=ward_west, lat=12.93, lon=77.58)

    # Supervisor can manage EastZone reports, but not WestZone
    client.force_login(supervisor)
    assert client.get(reverse("officer_manage_report", kwargs={"report_id": report_east.pk})).status_code == 200
    assert client.get(reverse("officer_manage_report", kwargs={"report_id": report_west.pk})).status_code == 403

    # Admin can manage any report
    client.force_login(admin_user)
    assert client.get(reverse("officer_manage_report", kwargs={"report_id": report_east.pk})).status_code == 200
    assert client.get(reverse("officer_manage_report", kwargs={"report_id": report_west.pk})).status_code == 200

@pytest.mark.django_db
def test_registration_always_creates_citizen(client):
    resp = client.post(reverse("register"), {
        "username": "new_citizen",
        "email": "new_citizen@example.com",
        "phone": "9876543210",
        "password": "ComplexPassword123!",
        "password_confirm": "ComplexPassword123!",
    })
    assert resp.status_code == 302
    created = User.objects.get(username="new_citizen")
    assert created.role == User.Role.CITIZEN
    assert created.phone == "9876543210"
