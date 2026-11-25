"""Dashboard views."""
from django.shortcuts import render
from .services import get_dashboard_data


def dashboard_home(request):
    """Public dashboard — no personal data exposed."""
    data = get_dashboard_data()
    return render(request, "dashboard/home.html", {"dashboard": data})
