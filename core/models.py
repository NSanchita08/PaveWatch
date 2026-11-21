from django.db import models

class Ward(models.Model):
    name = models.CharField(max_length=120, unique=True)
    zone = models.CharField(max_length=80)
    centroid_lat = models.FloatField()
    centroid_lon = models.FloatField()

    def __str__(self):
        return self.name

class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    sla_days = models.PositiveSmallIntegerField(default=7)
    base_severity = models.PositiveSmallIntegerField(default=2)  # 1..3

    class Meta:
        verbose_name_plural = "categories"

    def __str__(self):
        return self.name

class POI(models.Model):
    class Type(models.TextChoices):
        SCHOOL = "school", "School"
        HOSPITAL = "hospital", "Hospital"
        BUS_STOP = "bus_stop", "Bus stop"
        METRO = "metro", "Metro station"

    name = models.CharField(max_length=160, blank=True)
    poi_type = models.CharField(max_length=12, choices=Type.choices)
    lat = models.FloatField()
    lon = models.FloatField()

    class Meta:
        indexes = [models.Index(fields=["lat", "lon"])]

    def __str__(self):
        return f"{self.name} ({self.poi_type})"
