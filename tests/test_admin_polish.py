import pytest
from django.urls import reverse
from django.contrib.auth import get_user_model
from core.models import Ward, Category
from reports.models import Report
from reports.admin import export_reports_to_csv

User = get_user_model()

@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        username="test_admin", password="password123", email="admin@example.com", role=User.Role.ADMIN
    )

@pytest.fixture
def sample_report(db, admin_user):
    ward = Ward.objects.create(name="AdminWard", zone="AdminZone", centroid_lat=12.9, centroid_lon=77.6)
    category = Category.objects.create(name="AdminCategory", sla_days=5, base_severity=2)
    return Report.objects.create(
        tracking_id="PW-2026-999999",
        reporter=admin_user,
        category=category,
        ward=ward,
        description="Testing admin CSV export",
        lat=12.91,
        lon=77.61,
        severity=2,
    )

def test_admin_category_changelist(client, admin_user, sample_report):
    client.force_login(admin_user)
    url = reverse("admin:core_category_changelist")
    response = client.get(url)
    assert response.status_code == 200
    assert "AdminCategory" in response.content.decode()

def test_admin_user_changelist_shows_profile_fields(client, admin_user):
    client.force_login(admin_user)
    url = reverse("admin:accounts_user_changelist")
    response = client.get(url)
    assert response.status_code == 200
    assert "Role" in response.content.decode()

def test_export_reports_to_csv(sample_report):
    qs = Report.objects.filter(pk=sample_report.pk)
    response = export_reports_to_csv(None, None, qs)
    assert response.status_code == 200
    assert response["Content-Type"] == "text/csv"
    assert "attachment; filename=" in response["Content-Disposition"]
    content = response.content.decode()
    assert "PW-2026-999999" in content
    assert "AdminCategory" in content
    assert "AdminWard" in content
    assert "AdminZone" in content
