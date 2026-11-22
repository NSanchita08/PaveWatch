from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from accounts import views as account_views
from django.contrib.auth.views import LoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('accounts/', include('accounts.urls')),
    path('login/', LoginView.as_view(template_name='accounts/login.html'), name='login'),
    path('logout/', account_views.user_logout, name='logout'),
    path('profile/', account_views.profile, name='profile'),
    path('', include('reports.urls')),
]
