from django.contrib import admin
from .models import Report, ReportPhoto, StatusHistory, Confirmation, Notification

class ReportPhotoInline(admin.TabularInline):
    model = ReportPhoto
    extra = 0

class StatusHistoryInline(admin.TabularInline):
    model = StatusHistory
    extra = 0
    readonly_fields = ("from_status", "to_status", "changed_by", "remark", "created_at")

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
