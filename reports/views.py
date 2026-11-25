"""PaveWatch report views."""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.http import JsonResponse

from accounts.models import User
from accounts.permissions import role_required
from .forms import ReportForm
from .images import process_upload
from .models import Report, ReportPhoto, Notification, Confirmation
from .services import (
    can_change_status, change_status, create_report,
    find_duplicates, add_confirmation, ALLOWED_TRANSITIONS
)


# ---------------------------------------------------------------------------
# Notification views
# ---------------------------------------------------------------------------

@login_required
def notifications_dropdown(request):
    """Render a dropdown list of unread notifications for the current user."""
    notifs = request.user.notifications.filter(is_read=False).order_by("-created_at")[:10]
    return render(request, "notifications_dropdown.html", {"notifications": notifs})


@login_required
def notifications_page(request):
    """Full notification list; mark all as read on visit."""
    notifs = request.user.notifications.order_by("-created_at")
    # Mark all unread as read
    request.user.notifications.filter(is_read=False).update(is_read=True)
    return render(request, "notifications.html", {"notifications": notifs})


# ---------------------------------------------------------------------------
# Officer views
# ---------------------------------------------------------------------------

@role_required(User.Role.OFFICER, User.Role.SUPERVISOR, User.Role.ADMIN)
def officer_queue(request):
    """Work queue — filtered by role."""
    user = request.user
    qs = Report.objects.select_related("category", "ward", "assigned_to").order_by(
        "-priority_score", "created_at"
    )
    if user.role == User.Role.OFFICER:
        qs = qs.filter(ward=user.ward)
    elif user.role == User.Role.SUPERVISOR:
        qs = qs.filter(ward__zone=user.zone)
    # Filters
    status_filter = request.GET.get("status", "")
    category_filter = request.GET.get("category", "")
    if status_filter:
        qs = qs.filter(status=status_filter)
    if category_filter:
        qs = qs.filter(category_id=category_filter)
    from core.models import Category
    return render(request, "officer/queue.html", {
        "reports": qs,
        "status_choices": Report.Status.choices,
        "categories": Category.objects.all(),
        "status_filter": status_filter,
        "category_filter": category_filter,
    })


@role_required(User.Role.OFFICER, User.Role.SUPERVISOR, User.Role.ADMIN)
def officer_manage_report(request, report_id):
    """Manage a single report — view details, change status, add after photo."""
    report = get_object_or_404(Report, pk=report_id)
    if not can_change_status(request.user, report):
        raise PermissionDenied("You do not have permission to manage this report.")

    allowed_next = list(ALLOWED_TRANSITIONS.get(report.status, set()))
    error = None

    if request.method == "POST":
        action = request.POST.get("action", "")

        # --- Add after photo ---
        if action == "add_photo":
            for uploaded in request.FILES.getlist("photos"):
                try:
                    content_file, _ = process_upload(uploaded)
                    photo = ReportPhoto(
                        report=report, kind=ReportPhoto.Kind.AFTER, uploaded_by=request.user
                    )
                    photo.image.save(content_file.name, content_file, save=True)
                except Exception as e:
                    error = str(e)
            if not error:
                messages.success(request, "After photo(s) uploaded.")
            return redirect("officer_manage_report", report_id=report.id)

        # --- Change status ---
        if action == "change_status":
            new_status = request.POST.get("new_status", "")
            remark = request.POST.get("remark", "").strip()
            try:
                change_status(report, new_status, request.user, remark)
                messages.success(request, f"Status updated to {new_status}.")
                return redirect("officer_manage_report", report_id=report.id)
            except Exception as e:
                error = str(e)

    photos_before = report.photos.filter(kind=ReportPhoto.Kind.BEFORE)
    photos_after = report.photos.filter(kind=ReportPhoto.Kind.AFTER)
    history = report.history.order_by("created_at")
    return render(request, "officer/manage.html", {
        "report": report,
        "allowed_next": allowed_next,
        "photos_before": photos_before,
        "photos_after": photos_after,
        "history": history,
        "error": error,
    })


@role_required(User.Role.OFFICER, User.Role.SUPERVISOR, User.Role.ADMIN)
def officer_change_status(request, report_id):
    """Stand-alone status change endpoint (also used from manage page)."""
    report = get_object_or_404(Report, pk=report_id)
    if not can_change_status(request.user, report):
        raise PermissionDenied("You cannot change status for this report.")
    if request.method == "POST":
        new_status = request.POST.get("status", "")
        remark = request.POST.get("remark", "")
        if new_status:
            try:
                change_status(report, new_status, request.user, remark)
                messages.success(request, f"Status updated to {new_status}.")
            except Exception as e:
                messages.error(request, str(e))
        return redirect("officer_manage_report", report_id=report.id)
    return render(request, "officer/status_form.html", {
        "report": report,
        "status_choices": Report.Status.choices,
    })


@role_required(User.Role.OFFICER)
def officer_assign_report(request, report_id):
    """Assign a report to self."""
    report = get_object_or_404(Report, pk=report_id)
    if not can_change_status(request.user, report):
        raise PermissionDenied("You cannot assign this report.")
    if request.method == "POST":
        report.assigned_to = request.user
        report.save()
        messages.success(request, "Report assigned to you.")
        return redirect("officer_manage_report", report_id=report.id)
    return render(request, "officer/assign.html", {"report": report})


@role_required(User.Role.OFFICER)
def officer_add_after_photos(request, report_id):
    """Upload after photos for a report."""
    report = get_object_or_404(Report, pk=report_id)
    if not can_change_status(request.user, report):
        raise PermissionDenied("You cannot add photos to this report.")
    if request.method == "POST":
        for uploaded in request.FILES.getlist("photos"):
            try:
                content_file, _ = process_upload(uploaded)
                photo = ReportPhoto(report=report, kind=ReportPhoto.Kind.AFTER, uploaded_by=request.user)
                photo.image.save(content_file.name, content_file, save=True)
            except Exception as e:
                messages.error(request, str(e))
        return redirect("officer_manage_report", report_id=report.id)
    return render(request, "officer/add_photos.html", {"report": report})


# ---------------------------------------------------------------------------
# Citizen report submission & verification
# ---------------------------------------------------------------------------

@login_required
def check_duplicates(request):
    """JSON endpoint returning nearby open reports with same category within DUPLICATE_RADIUS_M."""
    lat_val = request.GET.get("lat") or request.POST.get("lat")
    lon_val = request.GET.get("lon") or request.POST.get("lon")
    category_id = request.GET.get("category_id") or request.POST.get("category_id")

    if not lat_val or not lon_val or not category_id:
        return JsonResponse({"count": 0, "duplicates": []})

    try:
        lat = float(lat_val)
        lon = float(lon_val)
        cat_id = int(category_id)
    except (ValueError, TypeError):
        return JsonResponse({"count": 0, "duplicates": []})

    dups = find_duplicates(lat, lon, cat_id)
    from .geo import haversine_m
    data = []
    for r in dups:
        dist = round(haversine_m(lat, lon, r.lat, r.lon), 1)
        data.append({
            "id": r.pk,
            "tracking_id": r.tracking_id or f"Report #{r.pk}",
            "category": r.category.name if r.category else "",
            "landmark": r.landmark,
            "distance_m": dist,
            "status": r.status,
            "created_at": r.created_at.strftime("%d %b %Y"),
            "detail_url": f"/r/{r.pk}/",
        })
    return JsonResponse({"count": len(data), "duplicates": data})


@login_required
def report_confirm(request, pk):
    """Citizen confirms that the obstruction is still there."""
    report = get_object_or_404(Report, pk=pk)
    if request.method == "POST":
        if report.status not in Report.OPEN_STATUSES:
            messages.warning(request, "This report is not currently open.")
            return redirect("report_detail", pk=report.pk)

        conf, created = add_confirmation(report, request.user, kind=Confirmation.Kind.STILL_THERE)
        if created:
            messages.success(request, "Thank you! You confirmed this obstruction is still there.")
        else:
            messages.info(request, "You have already confirmed this report.")
    return redirect("report_detail", pk=report.pk)


@login_required
def report_feedback(request, pk):
    """Reporter submits FIXED or NOT_FIXED feedback on a RESOLVED report."""
    report = get_object_or_404(Report, pk=pk)
    if report.reporter != request.user:
        raise PermissionDenied("Only the reporter can submit resolution feedback.")

    if request.method == "POST":
        if report.status != Report.Status.RESOLVED:
            messages.warning(request, "Feedback can only be submitted on resolved reports.")
            return redirect("report_detail", pk=report.pk)

        feedback = request.POST.get("feedback", "")
        if feedback == "FIXED":
            Confirmation.objects.get_or_create(
                report=report, user=request.user, kind=Confirmation.Kind.FIXED
            )
            change_status(
                report, Report.Status.CLOSED, request.user, remark="Citizen confirmed fixed"
            )
            messages.success(request, "Thank you! The report has been closed.")
        elif feedback == "NOT_FIXED":
            Confirmation.objects.get_or_create(
                report=report, user=request.user, kind=Confirmation.Kind.NOT_FIXED
            )
            change_status(
                report, Report.Status.REOPENED, request.user, remark="Citizen reported not fixed"
            )
            messages.warning(request, "Report has been reopened for further action.")
        else:
            messages.error(request, "Invalid feedback option.")
    return redirect("report_detail", pk=report.pk)


@login_required
def report_create(request):
    """Create a new report (any authenticated user, citizen role preferred)."""
    if request.method == "POST":
        form = ReportForm(request.POST, request.FILES)
        if form.is_valid():
            lat = form.cleaned_data["lat"]
            lon = form.cleaned_data["lon"]
            photos_uploaded = request.FILES.getlist("photos")

            # Process each uploaded photo
            processed_photos = []
            exif_results = []
            photo_error = None
            for uploaded in photos_uploaded:
                try:
                    cf, exif = process_upload(uploaded)
                    processed_photos.append(cf)
                    exif_results.append(exif)
                except Exception as e:
                    photo_error = str(e)
                    break

            if photo_error:
                form.add_error(None, photo_error)
            else:
                affects = {
                    "wheelchair": form.cleaned_data.get("affects_wheelchair", False),
                    "visually_impaired": form.cleaned_data.get("affects_visually_impaired", False),
                    "elderly": form.cleaned_data.get("affects_elderly", False),
                    "children": form.cleaned_data.get("affects_children", False),
                }

                force_dup_id = request.POST.get("duplicate_of")
                force_duplicate_of = None
                if force_dup_id:
                    try:
                        force_duplicate_of = Report.objects.filter(pk=int(force_dup_id)).first()
                    except (ValueError, TypeError):
                        force_duplicate_of = None

                try:
                    report = create_report(
                        reporter=request.user,
                        category=form.cleaned_data["category"],
                        lat=lat,
                        lon=lon,
                        description=form.cleaned_data.get("description", ""),
                        landmark=form.cleaned_data.get("landmark", ""),
                        severity=form.cleaned_data.get("severity", 2),
                        affects=affects,
                        processed_photos=processed_photos,
                        exif_results=exif_results,
                        force_duplicate_of=force_duplicate_of,
                    )
                    messages.success(request, f"Report submitted! Tracking ID: {report.tracking_id}")
                    return redirect("report_detail", pk=report.pk)
                except Exception as e:
                    form.add_error(None, str(e))
    else:
        form = ReportForm()
    return render(request, "reports/create.html", {"form": form})


@login_required
def my_reports(request):
    """List reports submitted by the logged-in citizen."""
    qs = Report.objects.filter(reporter=request.user).order_by("-created_at").select_related(
        "category", "ward"
    )
    return render(request, "reports/my_list.html", {"reports": qs})


def track_reports(request):
    """Public report listing with optional filters and pagination."""
    qs = Report.objects.select_related("category", "ward").order_by("-created_at")
    status = request.GET.get("status", "")
    ward_id = request.GET.get("ward_id", "")
    severity = request.GET.get("severity", "")
    if status:
        qs = qs.filter(status=status)
    if ward_id:
        qs = qs.filter(ward_id=ward_id)
    if severity:
        qs = qs.filter(severity=severity)
    from django.core.paginator import Paginator
    paginator = Paginator(qs, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "reports/track.html", {
        "page_obj": page_obj,
        "filters": request.GET,
        "Report": Report,
    })


def report_detail(request, pk):
    """Public report detail — reporter identity is hidden from the public."""
    report = get_object_or_404(Report, pk=pk)
    photos = report.photos.all()
    history = report.history.order_by("created_at")
    still_there_count = report.confirmations.filter(kind=Confirmation.Kind.STILL_THERE).count()
    user_confirmed = False
    if request.user.is_authenticated:
        user_confirmed = report.confirmations.filter(
            user=request.user, kind=Confirmation.Kind.STILL_THERE
        ).exists()
    # Only show reporter to staff / the reporter themselves
    show_reporter = (
        request.user.is_authenticated
        and (request.user == report.reporter or request.user.role in [
            User.Role.OFFICER, User.Role.SUPERVISOR, User.Role.ADMIN
        ])
    )
    return render(request, "reports/detail.html", {
        "report": report,
        "photos": photos,
        "history": history,
        "show_reporter": show_reporter,
        "still_there_count": still_there_count,
        "user_confirmed": user_confirmed,
    })
