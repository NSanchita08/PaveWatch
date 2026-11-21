from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Role(models.TextChoices):
        CITIZEN = "CITIZEN", "Citizen"
        OFFICER = "OFFICER", "Ward Officer"
        SUPERVISOR = "SUPERVISOR", "Supervisor"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(max_length=12, choices=Role.choices, default=Role.CITIZEN)
    phone = models.CharField(max_length=15, blank=True)
    ward = models.ForeignKey("core.Ward", null=True, blank=True, on_delete=models.SET_NULL)
    zone = models.CharField(max_length=80, blank=True)
    points = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        if self.is_superuser and self.role != self.Role.ADMIN:
            self.role = self.Role.ADMIN
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username
