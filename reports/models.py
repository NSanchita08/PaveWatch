"""models for reports app"""

from django.conf import settings
from django.db import models


class Report(models.Model):
    title = models.CharField(max_length=200, blank=True, default='')
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED"
        ACKNOWLEDGED = "ACKNOWLEDGED"
        IN_PROGRESS = "IN_PROGRESS"
        RESOLVED = "RESOLVED"
        CLOSED = "CLOSED"
        REOPENED = "REOPENED"
        REJECTED = "REJECTED"

    # Core fields
    tracking_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="reports")
    category = models.ForeignKey("core.Category", on_delete=models.PROTECT, null=True, blank=True)
    description = models.TextField(blank=True)
    landmark = models.CharField(max_length=200, blank=True)
    lat = models.FloatField()
    lon = models.FloatField()
    ward = models.ForeignKey("core.Ward", null=True, on_delete=models.SET_NULL, related_name="reports")
    severity = models.PositiveSmallIntegerField(default=2)
    affects_wheelchair = models.BooleanField(default=False)
    affects_visually_impaired = models.BooleanField(default=False)
    affects_elderly = models.BooleanField(default=False)
    affects_children = models.BooleanField(default=False)
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    priority_score = models.FloatField(default=0, db_index=True)
    trust_score = models.PositiveSmallIntegerField(default=0)
    exif_ok = models.BooleanField(default=False)
    ai_label = models.CharField(max_length=80, blank=True)
    ai_confidence = models.FloatField(null=True, blank=True)
    duplicate_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="duplicates")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_reports")
    created_at = models.DateTimeField(auto_now_add=True)
    sla_due_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    escalated = models.BooleanField(default=False)

    OPEN_STATUSES = ["SUBMITTED", "ACKNOWLEDGED", "IN_PROGRESS", "REOPENED"]

    @property
    def is_verified(self) -> bool:
        return self.trust_score >= 50

    def __str__(self):
        return self.tracking_id or f"Report #{self.pk}"


class ReportPhoto(models.Model):
    class Kind(models.TextChoices):
        BEFORE = "BEFORE"
        AFTER = "AFTER"

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="reports/%Y/%m/")
    kind = models.CharField(max_length=6, choices=Kind.choices, default=Kind.BEFORE)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.kind} photo for {self.report}"


class StatusHistory(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=14, blank=True)
    to_status = models.CharField(max_length=14)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    remark = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "status histories"

    def __str__(self):
        return f"{self.report}: {self.from_status} -> {self.to_status}"


class Confirmation(models.Model):
    class Kind(models.TextChoices):
        STILL_THERE = "STILL_THERE"
        FIXED = "FIXED"
        NOT_FIXED = "NOT_FIXED"

    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="confirmations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("report", "user", "kind")

    def __str__(self):
        return f"{self.user} confirmed {self.kind} on {self.report}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    report = models.ForeignKey(Report, null=True, on_delete=models.CASCADE)
    message = models.CharField(max_length=250)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Notification for {self.user}: {self.message}"
