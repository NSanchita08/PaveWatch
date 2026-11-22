from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db import transaction
import uuid
from .forms import ReportForm
from .models import Report, ReportPhoto
from .services import can_change_status
from django.core.exceptions import PermissionDenied
from accounts.permissions import role_required
from accounts.models import User

# Officer views (existing)
@role_required(User.Role.OFFICER, User.Role.SUPERVISOR, User.Role.ADMIN)
def officer_queue(request):
    return render(request, "officer/queue.html", {})

@role_required(User.Role.OFFICER, User.Role.SUPERVISOR, User.Role.ADMIN)
def officer_manage_report(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    if not can_change_status(request.user, report):
        raise PermissionDenied("You do not have permission to manage reports for this ward.")
    return render(request, "officer/manage.html", {"report": report})

# Citizen report submission
@login_required
@role_required(User.Role.CITIZEN)
def report_create(request):
    """Create a new report (citizen role)."""
    if request.method == "POST":
        form = ReportForm(request.POST, request.FILES)
        if form.is_valid():
            # Cleaned location returns (lat, lon)
            lat, lon = form.cleaned_data["location"]
            report = form.save(commit=False)
            report.reporter = request.user
            report.lat = lat
            report.lon = lon
            # Generate a simple tracking ID (UUID4 short)
            report.tracking_id = uuid.uuid4().hex[:10].upper()
            report.save()
            # Handle multiple photos
            for uploaded in request.FILES.getlist("photos"):
                ReportPhoto.objects.create(report=report, image=uploaded)
            return redirect("my_reports")
    else:
        form = ReportForm()
    return render(request, "reports/create.html", {"form": form})

@login_required
@role_required(User.Role.CITIZEN)
def my_reports(request):
    """List reports submitted by the logged‑in citizen."""
    qs = Report.objects.filter(reporter=request.user).order_by("-created_at")
    return render(request, "reports/my_list.html", {"reports": qs})
