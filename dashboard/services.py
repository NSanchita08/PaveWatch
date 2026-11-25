"""Dashboard aggregation service."""
import json
from django.db.models import Count, Avg
from reports.models import Report


def get_dashboard_data() -> dict:
    """Return aggregated data for the public dashboard. No personal data included."""
    qs = Report.objects.all()

    total = qs.count()
    open_count = qs.filter(status__in=Report.OPEN_STATUSES).count()
    resolved_count = qs.filter(status__in=["RESOLVED", "CLOSED"]).count()
    resolution_rate = round(resolved_count / total * 100, 1) if total > 0 else 0

    status_counts_dict = dict(
        qs.values("status").annotate(c=Count("id")).values_list("status", "c")
    )
    ward_counts_qs = (
        qs.values("ward__name")
        .annotate(c=Count("id"))
        .exclude(ward__name=None)
        .order_by("-c")
    )
    ward_counts_dict = {item["ward__name"]: item["c"] for item in ward_counts_qs}

    avg_vals = qs.aggregate(avg_priority=Avg("priority_score"), avg_trust=Avg("trust_score"))

    # Map markers — no reporter data
    reports_list = list(qs.values("lat", "lon", "tracking_id", "status", "id"))
    for r in reports_list:
        r["pk"] = r.pop("id", None)

    return {
        "total": total,
        "open": open_count,
        "resolved": resolved_count,
        "resolution_rate": resolution_rate,
        # JSON strings for JS charts/map
        "status_counts": json.dumps(status_counts_dict),
        "ward_counts_json": json.dumps(ward_counts_dict),
        "reports": json.dumps(reports_list),
        # Python dicts for template leaderboard
        "ward_leaderboard": ward_counts_dict,
        "avg_priority": avg_vals.get("avg_priority") or 0,
        "avg_trust": avg_vals.get("avg_trust") or 0,
    }
