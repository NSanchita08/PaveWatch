from django.urls import path
from . import views

urlpatterns = [
    # Citizen
    path("report/new/", views.report_create, name="report_create"),
    path("report/check-duplicates/", views.check_duplicates, name="check_duplicates"),
    path("api/suggest/", views.api_suggest, name="api_suggest"),
    path("api/geocode/", views.api_geocode, name="api_geocode"),
    path("my/", views.my_reports, name="my_reports"),
    path("track/", views.track_reports, name="track_reports"),
    path("route-check/", views.route_check, name="route_check"),
    path("r/<int:pk>/", views.report_detail, name="report_detail"),
    path("r/<int:pk>/confirm/", views.report_confirm, name="report_confirm"),
    path("r/<int:pk>/feedback/", views.report_feedback, name="report_feedback"),

    # Officer
    path("officer/", views.officer_queue, name="officer_queue"),
    path("officer/r/<int:report_id>/", views.officer_manage_report, name="officer_manage_report"),
    path("officer/assign/<int:report_id>/", views.officer_assign_report, name="officer_assign_report"),
    path("officer/status/<int:report_id>/", views.officer_change_status, name="officer_change_status"),
    path("officer/photos/<int:report_id>/", views.officer_add_after_photos, name="officer_add_photos"),

    # Notifications
    path("notifications/", views.notifications_page, name="notifications"),
    path("notifications/dropdown/", views.notifications_dropdown, name="notifications_dropdown"),
]
