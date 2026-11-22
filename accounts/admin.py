from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (
        ("PaveWatch Profile", {"fields": ("role", "phone", "ward", "zone", "points")}),
    )
    list_display = ("username", "email", "role", "ward", "zone", "points", "is_staff")
    list_filter = ("role", "ward", "zone", "is_staff", "is_superuser")
    search_fields = ("username", "email", "phone")
