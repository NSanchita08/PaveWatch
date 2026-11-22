"""PaveWatch business logic and services."""
from django.contrib.auth import get_user_model

User = get_user_model()

def can_change_status(user, report) -> bool:
    """ADMIN: always. SUPERVISOR: report.ward.zone == user.zone. OFFICER: report.ward_id == user.ward_id."""
    if not user or not user.is_authenticated:
        return False
    if user.role == User.Role.ADMIN:
        return True
    if user.role == User.Role.SUPERVISOR:
        return bool(report.ward and report.ward.zone and report.ward.zone == user.zone)
    if user.role == User.Role.OFFICER:
        return bool(report.ward_id and report.ward_id == user.ward_id)
    return False
