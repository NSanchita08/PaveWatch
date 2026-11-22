from django.urls import path
from . import views

urlpatterns = [
    path("officer/", views.officer_queue, name="officer_queue"),
    path("officer/r/<int:report_id>/", views.officer_manage_report, name="officer_manage_report"),
    path("report/new/", views.report_create, name="report_create"),
    path("my/", views.my_reports, name="my_reports"),
]
