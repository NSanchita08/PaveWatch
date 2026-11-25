import pytest
from django.urls import reverse
from django.test import Client
from django.contrib.auth import get_user_model
from reports.models import Report, Notification, ReportPhoto
from accounts.models import User

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        username="testcitizen", password="testpass", role=User.Role.CITIZEN
    )


@pytest.fixture
def officer(db):
    return User.objects.create_user(
        username="testofficer", password="testpass", role=User.Role.OFFICER
    )


@pytest.fixture
def client_obj():
    return Client()


@pytest.fixture
def report(db, user):
    """Minimal report (no title field in model)."""
    from core.models import Category
    cat, _ = Category.objects.get_or_create(name="Others", defaults={"sla_days": 7, "base_severity": 2})
    return Report.objects.create(
        description="Large pothole on Main St",
        reporter=user,
        lat=12.9716,
        lon=77.5946,
        severity=3,
        category=cat,
    )


def test_notification_created_on_status_change(db, officer, report):
    """Walk through the full valid transition chain to RESOLVED and check notification."""
    from reports.services import change_status

    # Proper transition chain: SUBMITTED → ACKNOWLEDGED → IN_PROGRESS → RESOLVED
    change_status(report, Report.Status.ACKNOWLEDGED, officer, remark="Acknowledged")
    change_status(report, Report.Status.IN_PROGRESS, officer, remark="Work started")

    # Add an AFTER photo so RESOLVED is accepted
    from io import BytesIO
    from PIL import Image
    from django.core.files.base import ContentFile

    img_buf = BytesIO()
    Image.new("RGB", (100, 100), color=(0, 200, 0)).save(img_buf, format="JPEG")
    cf = ContentFile(img_buf.getvalue(), name="after.jpg")
    photo = ReportPhoto(report=report, kind=ReportPhoto.Kind.AFTER, uploaded_by=officer)
    photo.image.save(cf.name, cf, save=True)

    change_status(report, Report.Status.RESOLVED, officer, remark="Fixed")

    assert Notification.objects.filter(user=report.reporter).exists()


def test_notifications_dropdown_view(db, user):
    client = Client()
    client.login(username="testcitizen", password="testpass")
    Notification.objects.create(user=user, message="Your report was updated", is_read=False)
    response = client.get(reverse("notifications_dropdown"))
    assert response.status_code == 200
    assert b"Your report was updated" in response.content


def test_notifications_page_view(db, user):
    client = Client()
    client.login(username="testcitizen", password="testpass")
    Notification.objects.create(user=user, message="Test notification", is_read=False)
    response = client.get(reverse("notifications"))
    assert response.status_code == 200
    assert b"Test notification" in response.content
