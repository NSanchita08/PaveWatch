from django.shortcuts import render, get_object_or_404
from django.core.exceptions import PermissionDenied
from accounts.permissions import role_required
from accounts.models import User
from .models import Report
from .services import can_change_status

@role_required(User.Role.OFFICER, User.Role.SUPERVISOR, User.Role.ADMIN)
def officer_queue(request):
    return render(request, "officer/queue.html", {})

@role_required(User.Role.OFFICER, User.Role.SUPERVISOR, User.Role.ADMIN)
def officer_manage_report(request, report_id):
    report = get_object_or_404(Report, pk=report_id)
    if not can_change_status(request.user, report):
        raise PermissionDenied("You do not have permission to manage reports for this ward.")
    return render(request, "officer/manage.html", {"report": report})
