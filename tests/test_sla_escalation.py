"""Tests for STEP 13: SLA countdown, escalate_overdue, citizen feedback, auto_close, and ward_scores."""
import pytest
from datetime import timedelta
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from core.models import Ward, Category
from reports.models import Report, ReportPhoto, StatusHistory, Notification
from reports.services import create_report, change_status, ward_scores


@pytest.fixture
def ward(db):
    return Ward.objects.create(
        name="Indiranagar", zone="East", centroid_lat=12.9784, centroid_lon=77.6408
    )


@pytest.fixture
def category(db):
    return Category.objects.create(name="Illegal Parking", sla_days=2, base_severity=2)


@pytest.fixture
def citizen(db, ward):
    return User.objects.create_user(
        username="sla_citizen",
        email="sla_citizen@example.com",
        password="password123",
        role=User.Role.CITIZEN,
        ward=ward,
    )


@pytest.fixture
def other_citizen(db, ward):
    return User.objects.create_user(
        username="sla_other",
        email="sla_other@example.com",
        password="password123",
        role=User.Role.CITIZEN,
        ward=ward,
    )


@pytest.fixture
def officer(db, ward):
    return User.objects.create_user(
        username="sla_officer",
        email="sla_officer@example.com",
        password="password123",
        role=User.Role.OFFICER,
        ward=ward,
    )


@pytest.fixture
def supervisor(db):
    return User.objects.create_user(
        username="sla_supervisor",
        email="sla_supervisor@example.com",
        password="password123",
        role=User.Role.SUPERVISOR,
        zone="East",
    )


@pytest.mark.django_db
def test_overdue_report_escalated_exactly_once(citizen, officer, supervisor, category):
    """Overdue open report gets escalated once with StatusHistory 'Auto-escalated' and notifications."""
    report = create_report(
        reporter=citizen,
        category=category,
        lat=12.9784,
        lon=77.6408,
        description="Blocked footpath",
        landmark="100ft Rd",
        severity=2,
        affects={},
        processed_photos=[ContentFile(b"img", name="p.jpg")],
        exif_results=[(None, None, None)],
    )
    # Make report overdue
    report.sla_due_at = timezone.now() - timedelta(days=3)
    report.save(update_fields=["sla_due_at"])
    assert report.is_overdue is True
    assert "Overdue by 3 days" in report.sla_status_label

    # Clear initial creation notifications
    Notification.objects.all().delete()

    # First run of escalate_overdue
    call_command("escalate_overdue")
    report.refresh_from_db()
    assert report.escalated is True

    esc_history = StatusHistory.objects.filter(report=report, remark="Auto-escalated")
    assert esc_history.count() == 1
    assert esc_history.first().from_status == report.status
    assert esc_history.first().to_status == report.status

    assert Notification.objects.filter(user=officer, report=report).exists()
    assert Notification.objects.filter(user=supervisor, report=report).exists()

    # Second run should NOT escalate again
    call_command("escalate_overdue")
    assert StatusHistory.objects.filter(report=report, remark="Auto-escalated").count() == 1


@pytest.mark.django_db
def test_citizen_feedback_not_fixed_reopens_and_fixed_closes(
    client, citizen, other_citizen, officer, category
):
    """NOT_FIXED reopens a RESOLVED report; FIXED closes it; non-reporter gets 403."""
    def make_resolved_report():
        r = create_report(
            reporter=citizen,
            category=category,
            lat=12.9784,
            lon=77.6408,
            description="Debris",
            landmark="CMH Rd",
            severity=2,
            affects={},
            processed_photos=[ContentFile(b"img", name="b.jpg")],
            exif_results=[(None, None, None)],
        )
        change_status(r, Report.Status.ACKNOWLEDGED, officer, "Ack")
        change_status(r, Report.Status.IN_PROGRESS, officer, "Working")
        after_photo = ReportPhoto(report=r, kind=ReportPhoto.Kind.AFTER, uploaded_by=officer)
        after_photo.image.save("after.jpg", ContentFile(b"after"), save=True)
        change_status(r, Report.Status.RESOLVED, officer, "Cleared")
        return r

    r1 = make_resolved_report()
    url1 = reverse("report_feedback", args=[r1.pk])

    # Non-reporter is forbidden
    client.force_login(other_citizen)
    resp_forbidden = client.post(url1, {"feedback": "NOT_FIXED"})
    assert resp_forbidden.status_code == 403

    # Reporter submits NOT_FIXED -> REOPENED
    client.force_login(citizen)
    resp_reopen = client.post(url1, {"feedback": "NOT_FIXED"})
    assert resp_reopen.status_code == 302
    r1.refresh_from_db()
    assert r1.status == Report.Status.REOPENED

    # Reporter submits FIXED -> CLOSED
    r2 = make_resolved_report()
    url2 = reverse("report_feedback", args=[r2.pk])
    resp_close = client.post(url2, {"feedback": "FIXED"})
    assert resp_close.status_code == 302
    r2.refresh_from_db()
    assert r2.status == Report.Status.CLOSED
    assert r2.closed_at is not None


@pytest.mark.django_db
def test_auto_close_stale_resolved_reports(citizen, officer, category):
    """auto_close closes RESOLVED reports older than AUTO_CLOSE_DAYS with no feedback."""
    r_old = create_report(
        reporter=citizen,
        category=category,
        lat=12.9784,
        lon=77.6408,
        description="Old resolved",
        landmark="Park",
        severity=1,
        affects={},
        processed_photos=[ContentFile(b"img", name="b.jpg")],
        exif_results=[(None, None, None)],
    )
    change_status(r_old, Report.Status.ACKNOWLEDGED, officer, "Ack")
    change_status(r_old, Report.Status.IN_PROGRESS, officer, "In prog")
    p = ReportPhoto(report=r_old, kind=ReportPhoto.Kind.AFTER, uploaded_by=officer)
    p.image.save("a.jpg", ContentFile(b"after"), save=True)
    change_status(r_old, Report.Status.RESOLVED, officer, "Done")
    r_old.resolved_at = timezone.now() - timedelta(days=10)
    r_old.save(update_fields=["resolved_at"])

    r_recent = create_report(
        reporter=citizen,
        category=category,
        lat=12.9784,
        lon=77.6408,
        description="Recent resolved",
        landmark="Metro",
        severity=1,
        affects={},
        processed_photos=[ContentFile(b"img", name="b2.jpg")],
        exif_results=[(None, None, None)],
    )
    change_status(r_recent, Report.Status.ACKNOWLEDGED, officer, "Ack")
    change_status(r_recent, Report.Status.IN_PROGRESS, officer, "In prog")
    p2 = ReportPhoto(report=r_recent, kind=ReportPhoto.Kind.AFTER, uploaded_by=officer)
    p2.image.save("a2.jpg", ContentFile(b"after2"), save=True)
    change_status(r_recent, Report.Status.RESOLVED, officer, "Done")

    call_command("auto_close")
    r_old.refresh_from_db()
    r_recent.refresh_from_db()
    assert r_old.status == Report.Status.CLOSED
    assert r_recent.status == Report.Status.RESOLVED


@pytest.mark.django_db
def test_ward_scores_guards_zero_division(ward, citizen, category):
    """ward_scores handles empty wards and mixed on-time/overdue reports cleanly."""
    # Empty ward
    scores = ward_scores()
    assert len(scores) == 1
    assert scores[0]["reliability"] == 100.0

    # Add 1 overdue open report
    r = create_report(
        reporter=citizen,
        category=category,
        lat=12.9784,
        lon=77.6408,
        description="Overdue",
        landmark="Road",
        severity=2,
        affects={},
        processed_photos=[ContentFile(b"img", name="b.jpg")],
        exif_results=[(None, None, None)],
    )
    r.sla_due_at = timezone.now() - timedelta(days=1)
    r.save(update_fields=["sla_due_at"])

    scores_after = ward_scores()
    # on_time_resolved_share = 1.0 (0 resolved), overdue_open_share = 1/1 -> 70*1 + 30*(1-1) = 70.0
    assert scores_after[0]["reliability"] == 70.0
