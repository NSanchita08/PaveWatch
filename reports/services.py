"""PaveWatch business logic and services."""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.core.mail import send_mail

from .models import Report, ReportPhoto, StatusHistory, Notification, Confirmation

User = get_user_model()

ALLOWED_TRANSITIONS = {
    "SUBMITTED":    {"ACKNOWLEDGED", "REJECTED"},
    "ACKNOWLEDGED": {"IN_PROGRESS", "REJECTED"},
    "IN_PROGRESS":  {"RESOLVED"},
    "RESOLVED":     {"CLOSED", "REOPENED"},
    "REOPENED":     {"IN_PROGRESS"},
    "CLOSED":       set(),
    "REJECTED":     set(),
}


class InvalidTransition(Exception):
    pass


def can_change_status(user, report) -> bool:
    """ADMIN: always. SUPERVISOR: same zone. OFFICER: same ward."""
    if not user or not user.is_authenticated:
        return False
    if user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.SUPERVISOR:
        return bool(report.ward and report.ward.zone and report.ward.zone == user.zone)
    if user.role == User.Role.OFFICER:
        return bool(report.ward_id and report.ward_id == user.ward_id)
    return False


def notify(user, report, message: str) -> None:
    """Create a Notification row for user."""
    Notification.objects.create(user=user, report=report, message=message)


@transaction.atomic
def change_status(report, new_status, changed_by, remark: str = "") -> Report:
    """
    Change a report's status through the canonical service.

    - Validates the transition against ALLOWED_TRANSITIONS.
    - RESOLVED requires an AFTER photo and a remark.
    - REJECTED requires a remark.
    - Sets resolved_at / closed_at timestamps.
    - Writes StatusHistory.
    - Creates a Notification for the reporter.
    - Attempts to send email (try/except — never blocks saving).
    """
    old_status = report.status
    allowed = ALLOWED_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        raise InvalidTransition(
            f"Cannot transition from {old_status} to {new_status}. "
            f"Allowed: {allowed}"
        )

    # RESOLVED requires an AFTER photo and a remark
    if new_status == Report.Status.RESOLVED:
        has_after = report.photos.filter(kind=ReportPhoto.Kind.AFTER).exists()
        if not has_after:
            raise ValueError("RESOLVED requires an AFTER photo.")
        if not remark.strip():
            raise ValueError("RESOLVED requires a remark.")

    # REJECTED requires a remark
    if new_status == Report.Status.REJECTED and not remark.strip():
        raise ValueError("REJECTED requires a remark.")

    # Timestamps
    now = timezone.now()
    if new_status == Report.Status.RESOLVED:
        report.resolved_at = now
    if new_status == Report.Status.CLOSED:
        report.closed_at = now

    report.status = new_status
    report.save()

    StatusHistory.objects.create(
        report=report,
        from_status=old_status,
        to_status=new_status,
        changed_by=changed_by,
        remark=remark,
    )

    # Notify reporter
    if report.reporter:
        msg = f"Your report {report.tracking_id or report.pk} status changed to {new_status}."
        if remark:
            msg += f" Note: {remark}"
        notify(report.reporter, report, msg)

        # Try email — must never break saving
        try:
            if report.reporter.email:
                send_mail(
                    subject=f"PaveWatch: Report {report.tracking_id or report.pk} updated",
                    message=msg,
                    from_email="noreply@pavewatch.local",
                    recipient_list=[report.reporter.email],
                    fail_silently=True,
                )
        except Exception:
            pass

    return report


def find_duplicates(lat, lon, category_id):
    """Return open reports of same category within DUPLICATE_RADIUS_M (bbox + haversine)."""
    from django.conf import settings
    from .geo import haversine_m, bbox

    radius = getattr(settings, "DUPLICATE_RADIUS_M", 50)
    lat_min, lat_max, lon_min, lon_max = bbox(lat, lon, radius)
    candidates = Report.objects.filter(
        category_id=category_id,
        status__in=Report.OPEN_STATUSES,
        lat__range=(lat_min, lat_max),
        lon__range=(lon_min, lon_max),
    )
    return [r for r in candidates if haversine_m(lat, lon, r.lat, r.lon) <= radius]


def compute_priority(report) -> float:
    """
    score = severity*10
          + 15 if school POI within 300 m
          + 15 if hospital POI within 300 m
          + 10 if bus_stop or metro POI within 200 m
          + 5 per ticked affects_* box
          + min(2 * STILL_THERE confirmations, 10)
          + min(days_open, 15)
    """
    from .geo import haversine_m, bbox
    from core.models import POI

    score = float(report.severity * 10)

    lat_min, lat_max, lon_min, lon_max = bbox(report.lat, report.lon, 300)
    pois = list(
        POI.objects.filter(lat__range=(lat_min, lat_max), lon__range=(lon_min, lon_max))
    )
    near_school = any(
        haversine_m(report.lat, report.lon, p.lat, p.lon) <= 300
        for p in pois if p.poi_type == POI.Type.SCHOOL
    )
    near_hospital = any(
        haversine_m(report.lat, report.lon, p.lat, p.lon) <= 300
        for p in pois if p.poi_type == POI.Type.HOSPITAL
    )
    near_transit = any(
        haversine_m(report.lat, report.lon, p.lat, p.lon) <= 200
        for p in pois if p.poi_type in (POI.Type.BUS_STOP, POI.Type.METRO)
    )

    if near_school:
        score += 15
    if near_hospital:
        score += 15
    if near_transit:
        score += 10

    for field in ("affects_wheelchair", "affects_visually_impaired", "affects_elderly", "affects_children"):
        if getattr(report, field, False):
            score += 5

    confirmations = report.confirmations.filter(kind="STILL_THERE").count()
    score += min(2 * confirmations, 10)

    if report.created_at:
        days_open = max((timezone.now() - report.created_at).days, 0)
        score += min(days_open, 15)

    return score


def nearby_pois(report, max_distance_m: int = 300) -> list[dict]:
    """Return POIs within max_distance_m of report, sorted by distance ascending."""
    from .geo import haversine_m, bbox
    from core.models import POI

    lat_min, lat_max, lon_min, lon_max = bbox(report.lat, report.lon, max_distance_m)
    candidates = POI.objects.filter(
        lat__range=(lat_min, lat_max),
        lon__range=(lon_min, lon_max),
    )
    results = []
    for p in candidates:
        dist = haversine_m(report.lat, report.lon, p.lat, p.lon)
        if dist <= max_distance_m:
            results.append({
                "poi": p,
                "name": p.name,
                "poi_type": p.poi_type,
                "poi_type_label": p.get_poi_type_display(),
                "distance_m": round(dist),
            })
    results.sort(key=lambda item: item["distance_m"])
    return results


def recalc_all_priorities(include_closed: bool = False) -> int:
    """Recalculate priority_score for open reports (or all reports if include_closed=True)."""
    qs = Report.objects.all() if include_closed else Report.objects.filter(status__in=Report.OPEN_STATUSES)
    updated = 0
    for report in qs:
        new_score = compute_priority(report)
        if report.priority_score != new_score:
            report.priority_score = new_score
            report.save(update_fields=["priority_score"])
            updated += 1
    return updated


def compute_trust(report) -> int:
    """
    +30 GPS matches, +20 timestamp fresh, +20 ai_label == category,
    +min(5*confirmations, 20), +10 if reporter has prior CLOSED report. Cap 100.
    """
    score = 0
    if report.exif_ok:
        score += 30 + 20  # GPS + timestamp both baked into exif_ok
    if report.ai_label and report.category and report.ai_label.strip().lower() == report.category.name.strip().lower():
        score += 20
    confirmations = report.confirmations.filter(kind="STILL_THERE").count()
    score += min(5 * confirmations, 20)
    if report.reporter:
        prior_qs = Report.objects.filter(reporter=report.reporter, status=Report.Status.CLOSED)
        if report.pk:
            prior_qs = prior_qs.exclude(pk=report.pk)
        if prior_qs.exists():
            score += 10
    return min(score, 100)


@transaction.atomic
def add_confirmation(report: Report, user, kind: str = "STILL_THERE") -> tuple[Confirmation, bool]:
    """
    Record a confirmation from user.
    One per user per report per kind (enforced by DB unique_together).
    Recalculates priority_score and trust_score on the report if newly created.
    """
    conf, created = Confirmation.objects.get_or_create(
        report=report,
        user=user,
        kind=kind,
    )
    if created:
        report.priority_score = compute_priority(report)
        report.trust_score = compute_trust(report)
        report.save(update_fields=["priority_score", "trust_score"])
    return conf, created


def _ward_open_priority_sums() -> dict[int, float]:
    """Return mapping of ward_id -> sum of priority_score for open reports."""
    from core.models import Ward
    from django.db.models import Sum

    sums = dict(
        Report.objects.filter(status__in=Report.OPEN_STATUSES, ward__isnull=False)
        .values("ward_id")
        .annotate(total_priority=Sum("priority_score"))
        .values_list("ward_id", "total_priority")
    )
    return {w.id: float(sums.get(w.id) or 0.0) for w in Ward.objects.all()}


def accessibility_score(ward) -> float:
    """
    Compute accessibility score for a ward:
    100 * (1 - ward_open_priority_sum / max_ward_open_priority_sum),
    or 100.0 if max_ward_open_priority_sum is 0.
    """
    sums = _ward_open_priority_sums()
    if not sums:
        return 100.0
    max_sum = max(sums.values())
    if max_sum <= 0:
        return 100.0
    ward_sum = sums.get(ward.id, 0.0)
    return round(100.0 * (1.0 - ward_sum / max_sum), 1)


def ward_scores() -> list[dict]:
    """
    Compute reliability and accessibility scores per ward:
    reliability = 70 * on_time_resolved_share + 30 * (1 - overdue_open_share)
    accessibility = 100 * (1 - ward_open_priority_sum / max_ward_open_priority_sum)
    (with divide-by-zero guards).
    """
    from core.models import Ward
    from django.db.models import F

    now = timezone.now()
    priority_sums = _ward_open_priority_sums()
    max_priority_sum = max(priority_sums.values(), default=0.0)

    results = []
    for ward in Ward.objects.all():
        ward_reports = Report.objects.filter(ward=ward)
        total = ward_reports.count()

        resolved_qs = ward_reports.filter(
            status__in=[Report.Status.RESOLVED, Report.Status.CLOSED]
        )
        resolved_count = resolved_qs.count()
        on_time_resolved = resolved_qs.filter(
            resolved_at__isnull=False,
            sla_due_at__isnull=False,
            resolved_at__lte=F("sla_due_at"),
        ).count()
        on_time_resolved_share = (
            on_time_resolved / resolved_count if resolved_count > 0 else 1.0
        )

        open_qs = ward_reports.filter(status__in=Report.OPEN_STATUSES)
        open_count = open_qs.count()
        overdue_open = open_qs.filter(sla_due_at__lt=now).count()
        overdue_open_share = (
            overdue_open / open_count if open_count > 0 else 0.0
        )

        reliability = round(
            70.0 * on_time_resolved_share + 30.0 * (1.0 - overdue_open_share), 1
        )
        ward_sum = priority_sums.get(ward.id, 0.0)
        accessibility = (
            round(100.0 * (1.0 - ward_sum / max_priority_sum), 1)
            if max_priority_sum > 0
            else 100.0
        )
        results.append({
            "ward": ward,
            "ward_name": ward.name,
            "total": total,
            "open_count": open_count,
            "resolved_count": resolved_count,
            "overdue_open": overdue_open,
            "reliability": reliability,
            "accessibility": accessibility,
        })
    results.sort(key=lambda x: (-x["reliability"], -x["total"], x["ward_name"]))
    return results


def escalate_overdue_reports() -> int:
    """
    For open reports with sla_due_at < now and escalated=False:
    - Set escalated=True
    - Notify ward officer(s) (plus assigned_to) and zone supervisor(s)
    - Insert direct StatusHistory row with remark 'Auto-escalated' (same status -> same status)
    Returns count of escalated reports.
    """
    now = timezone.now()
    overdue_qs = Report.objects.filter(
        status__in=Report.OPEN_STATUSES,
        sla_due_at__lt=now,
        escalated=False,
    ).select_related("ward", "assigned_to")

    count = 0
    for report in overdue_qs:
        with transaction.atomic():
            report.escalated = True
            report.save(update_fields=["escalated"])

            StatusHistory.objects.create(
                report=report,
                from_status=report.status,
                to_status=report.status,
                changed_by=None,
                remark="Auto-escalated",
            )

            recipients = set()
            if report.assigned_to:
                recipients.add(report.assigned_to)
            if report.ward:
                for officer in User.objects.filter(role=User.Role.OFFICER, ward=report.ward):
                    recipients.add(officer)
                if report.ward.zone:
                    for supervisor in User.objects.filter(role=User.Role.SUPERVISOR, zone=report.ward.zone):
                        recipients.add(supervisor)

            msg = f"SLA overdue: Report {report.tracking_id or report.pk} has been auto-escalated."
            for user in recipients:
                notify(user, report, msg)

            count += 1
    return count


def auto_close_resolved_reports() -> int:
    """
    Close RESOLVED reports older than AUTO_CLOSE_DAYS with no citizen feedback.
    Returns count of auto-closed reports.
    """
    from datetime import timedelta
    from django.conf import settings

    auto_close_days = getattr(settings, "AUTO_CLOSE_DAYS", 7)
    cutoff = timezone.now() - timedelta(days=auto_close_days)

    stale_qs = (
        Report.objects.filter(
            status=Report.Status.RESOLVED,
            resolved_at__lt=cutoff,
        )
        .exclude(confirmations__kind__in=[Confirmation.Kind.FIXED, Confirmation.Kind.NOT_FIXED])
        .distinct()
    )

    count = 0
    for report in stale_qs:
        change_status(
            report,
            Report.Status.CLOSED,
            changed_by=None,
            remark=f"Auto-closed after {auto_close_days} days with no citizen feedback",
        )
        count += 1
    return count


@transaction.atomic
def create_report(*, reporter, category, lat, lon, description, landmark,
                  severity, affects, processed_photos, exif_results,
                  force_duplicate_of=None, ai_label: str = "",
                  ai_confidence: float | None = None) -> Report:
    """
    1. Create Report (ward = nearest_ward, sla_due_at = now + category.sla_days).
    2. Set tracking_id = f"PW-{year}-{pk:06d}" and save again.
    3. Save each ReportPhoto (kind BEFORE).
    4. exif_ok = any photo with GPS within EXIF_MAX_DISTANCE_M AND taken within EXIF_MAX_AGE_HOURS.
    5. duplicate_of = force_duplicate_of.
    6. priority_score = compute_priority; trust_score = compute_trust.
    7. First StatusHistory row.
    8. Notify ward officers.
    """
    from .geo import nearest_ward
    from django.conf import settings

    if reporter is not None:
        max_per_day = getattr(settings, "MAX_REPORTS_PER_DAY", 20)
        since = timezone.now() - __import__("datetime").timedelta(days=1)
        recent_count = Report.objects.filter(reporter=reporter, created_at__gte=since).count()
        if recent_count >= max_per_day:
            raise ValueError(f"Daily report limit reached ({max_per_day} reports per day). Please try again tomorrow.")

    ward = nearest_ward(lat, lon)
    sla_due_at = timezone.now() + __import__('datetime').timedelta(days=category.sla_days)

    report = Report.objects.create(
        reporter=reporter,
        category=category,
        lat=lat,
        lon=lon,
        description=description,
        landmark=landmark,
        severity=severity,
        ward=ward,
        sla_due_at=sla_due_at,
        duplicate_of=force_duplicate_of,
        affects_wheelchair=affects.get("wheelchair", False),
        affects_visually_impaired=affects.get("visually_impaired", False),
        affects_elderly=affects.get("elderly", False),
        affects_children=affects.get("children", False),
        ai_label=(ai_label or "").strip()[:80],
        ai_confidence=ai_confidence,
    )

    year = report.created_at.year
    report.tracking_id = f"PW-{year}-{report.pk:06d}"

    # EXIF check
    exif_ok = False
    exif_max_dist = getattr(settings, "EXIF_MAX_DISTANCE_M", 100)
    exif_max_age = getattr(settings, "EXIF_MAX_AGE_HOURS", 48)
    for content_file, (exif_lat, exif_lon, exif_taken) in zip(processed_photos, exif_results):
        if exif_lat is not None and exif_lon is not None:
            from .geo import haversine_m
            dist = haversine_m(lat, lon, exif_lat, exif_lon)
            if dist <= exif_max_dist:
                if exif_taken:
                    if timezone.is_naive(exif_taken):
                        exif_taken_aware = timezone.make_aware(exif_taken)
                    else:
                        exif_taken_aware = exif_taken
                    age_hours = (timezone.now() - exif_taken_aware).total_seconds() / 3600
                    if -1 <= age_hours <= exif_max_age:
                        exif_ok = True
    report.exif_ok = exif_ok

    report.priority_score = compute_priority(report)
    report.trust_score = compute_trust(report)
    report.save()

    for content_file, _ in zip(processed_photos, exif_results):
        photo = ReportPhoto(report=report, kind=ReportPhoto.Kind.BEFORE, uploaded_by=reporter)
        photo.image.save(content_file.name, content_file, save=True)

    StatusHistory.objects.create(
        report=report,
        from_status="",
        to_status=Report.Status.SUBMITTED,
        changed_by=reporter,
        remark="Report submitted",
    )

    # Notify ward officers
    if ward:
        officers = User.objects.filter(role=User.Role.OFFICER, ward=ward)
        for officer in officers:
            notify(officer, report, f"New report {report.tracking_id} in your ward.")

    return report
