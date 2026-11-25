from django.contrib import admin
from .models import Ward, Category, POI

@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):
    list_display = ("name", "zone", "centroid_lat", "centroid_lon")
    list_filter = ("zone",)
    search_fields = ("name", "zone")

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "sla_days", "base_severity")
    list_editable = ("sla_days", "base_severity")
    list_filter = ("base_severity",)
    search_fields = ("name",)

@admin.register(POI)
class POIAdmin(admin.ModelAdmin):
    list_display = ("name", "poi_type", "lat", "lon")
    list_filter = ("poi_type",)
    search_fields = ("name",)
