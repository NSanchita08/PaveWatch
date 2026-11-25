import csv
from django.contrib import admin
from django.http import HttpResponse
from .models import Report, ReportPhoto, StatusHistory, Confirmation, Notification

@admin.action(description="Export selected reports to CSV")
def export_reports_to_csv(modeladmin, request, queryset):
    """Admin action to export selected reports to CSV without leaking sensitive reporter info."""
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="pavewatch_reports.csv"'
    writer = csv.writer(response)
    writer.writerow([
        "tracking_id",
        "category",
        "ward",
        "zone",
        "status",
        "severity",
        "priority_score",
        "trust_score",
        "lat",
        "lon",
        "escalated",
        "created_at",
        "sla_due_at",
        "resolved_at",
        "closed_at",
    ])
    for report in queryset.select_related("category", "ward"):
        writer.writerow([
            report.tracking_id or f"PW-{report.id}",
            report.category.name if report.category else "",
            report.ward.name if report.ward else "",
            report.ward.zone if report.ward else "",
            report.status,
            report.severity,
            report.priority_score,
            report.trust_score,
            report.lat,
            report.lon,
            report.escalated,
            report.created_at.strftime("%Y-%m-%d %H:%M:%S") if report.created_at else "",
            report.sla_due_at.strftime("%Y-%m-%d %H:%M:%S") if report.sla_due_at else "",
            report.resolved_at.strftime("%Y-%m-%d %H:%M:%S") if report.resolved_at else "",
            report.closed_at.strftime("%Y-%m-%d %H:%M:%S") if report.closed_at else "",
        ])
    return response

class ReportPhotoInline(admin.TabularInline):
    model = ReportPhoto
    extra = 0
    readonly_fields = ("uploaded_at",)

class StatusHistoryInline(admin.TabularInline):
    model = StatusHistory
    extra = 0
    readonly_fields = ("from_status", "to_status", "changed_by", "remark", "created_at")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "tracking_id",
        "category",
        "ward",
        "status",
        "severity",
        "priority_score",
        "trust_score",
        "escalated",
        "created_at",
    )
    list_filter = ("status", "category", "ward", "severity", "escalated", "created_at")
    search_fields = ("tracking_id", "description", "landmark")
    inlines = [ReportPhotoInline, StatusHistoryInline]
    actions = [export_reports_to_csv]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    list_per_page = 25
    list_select_related = ("category", "ward", "reporter")

@admin.register(ReportPhoto)
class ReportPhotoAdmin(admin.ModelAdmin):
    list_display = ("report", "kind", "uploaded_by", "uploaded_at")
    list_filter = ("kind",)

@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ("report", "from_status", "to_status", "changed_by", "created_at")
    list_filter = ("to_status",)
    search_fields = ("report__tracking_id", "remark")

@admin.register(Confirmation)
class ConfirmationAdmin(admin.ModelAdmin):
    list_display = ("report", "user", "kind", "created_at")
    list_filter = ("kind",)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "report", "message", "is_read", "created_at")
    list_filter = ("is_read",)
    search_fields = ("user__username", "message")
