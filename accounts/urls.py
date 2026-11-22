from django.urls import path
from django.contrib.auth.views import LoginView
from . import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", LoginView.as_view(template_name="accounts/login.html"), name="login"),
    path("logout/", views.user_logout, name="logout"),
    path("profile/", views.profile, name="profile"),
]
