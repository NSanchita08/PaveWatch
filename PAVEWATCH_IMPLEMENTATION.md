# PaveWatch: Implementation Instructions for a Coding Model

> Give this whole file to the coding model (Claude Code, Cursor, Copilot, etc.), then drive it **one step at a time** using the prompts in Section 2. Do not ask it to build everything at once.

---

## 0. Project summary

PaveWatch is a Django website where citizens report footpath obstructions (with photo and map pin), officers resolve them through a controlled workflow, and the public tracks progress on a dashboard.

Differentiators (build after the MVP works):
1. **Verified reports:** EXIF GPS/time check, duplicate detection, trust score.
2. **SLA escalation and citizen-confirmed closure.**
3. **Accessibility-aware priority:** schools, hospitals, bus stops and affected groups raise priority.
4. **AI photo assistant** (optional, never blocking) and **accessible route check** (stretch).

---

## 1. Rules for the coding model (read first, obey always)

1. Implement **only the step you are asked to do**. Do not start the next step.
2. Use **only** the stack and packages in Section 3. Do not add libraries, Node, npm, React, Celery, Redis, PostGIS or Docker.
3. Output **complete files**, not fragments, unless told to patch a named file.
4. After each step, run the listed checks (`python manage.py check`, `makemigrations --check`, `pytest`) and fix every error before reporting done.
5. Never edit a model without creating and applying a migration.
6. `AUTH_USER_MODEL = "accounts.User"` must be set **before the first migrate**. Never change it afterwards.
7. All status changes go through `reports.services.change_status()`. No view, admin action or command may assign `report.status` directly.
8. Every POST form includes `{% csrf_token %}`. Every view has a permission check (decorator plus object-level check).
9. Every external call (AI, email, route API) is wrapped in `try/except` with a timeout and must never break saving a report.
10. Never hard-code secrets. Read from environment variables via `python-dotenv`.
11. Do not ask clarifying questions. If something is unspecified, choose the simplest option, state the assumption in one line, and continue.
12. Keep code readable: type hints on service functions, docstrings on public functions, no dead code.
13. Use `timezone.now()` (timezone-aware). `TIME_ZONE = "Asia/Kolkata"`, `USE_TZ = True`.
14. Reporter identity (name, phone, email) must never appear on public pages or public JSON endpoints.

---

## 2. How to drive the model (prompts to paste)

Paste Sections 0, 1, 3, 4, 5 once at the start. Then, one at a time:

```
Implement STEP N from Section 8 of the spec exactly. Create or modify only the files listed.
When finished, run the checks listed for that step and show me the output.
Do not begin STEP N+1.
```

If something breaks:

```
Here is the full error traceback: <paste>. Fix the root cause. Do not change unrelated files.
Re-run the checks and show me the result.
```

After each step: commit to git (`git add -A && git commit -m "Step N: ..."`).

---

## 3. Stack and packages (fixed)

| Item | Choice |
|---|---|
| Python | 3.12 |
| Framework | Django 5.2 LTS |
| DB | SQLite in dev, PostgreSQL in prod (`DATABASE_URL` via `dj-database-url`) |
| Frontend | Django templates, Bootstrap 5.3.3, vanilla JS (no build step) |
| Maps | Leaflet 1.9.4 + OpenStreetMap tiles, Leaflet.markercluster 1.5.3 |
| Charts | Chart.js 4.4.x |
| Static | WhiteNoise |
| Server | Gunicorn |
| Images | Pillow (process), Cloudinary (prod storage) |
| Tests | pytest, pytest-django |

`requirements.txt` base (install latest compatible, then `pip freeze`):

```
django>=5.2,<5.3
pillow
python-dotenv
whitenoise
gunicorn
dj-database-url
psycopg[binary]
requests
anthropic
cloudinary
django-cloudinary-storage
pytest
pytest-django
```

CDN tags for `templates/base.html`:

```html
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
<!-- load only on pages that need maps -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css">
<link rel="stylesheet" href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.Default.css">
<script src="https://unpkg.com/leaflet.markercluster@1.5.3/dist/leaflet.markercluster.js"></script>
<!-- dashboard only -->
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
```

---

## 4. Repository layout

```
PaveWatch/
  config/              settings.py, urls.py, wsgi.py
  core/                models.py (Ward, Category, POI), management/commands/
  accounts/            models.py (User), forms.py, views.py, permissions.py, urls.py
  reports/             models.py, forms.py, services.py, geo.py, images.py, ai.py,
                       views.py, urls.py, management/commands/
  dashboard/           views.py (pages + JSON), urls.py
  templates/           base.html, accounts/, reports/, officer/, dashboard/
  static/              css/app.css, js/report_map.js, js/dashboard.js
  data/                wards.json, pois.json
  tests/
  legacy/app.py        (old Streamlit prototype, reference only)
  manage.py, requirements.txt, pytest.ini, .env.example, .gitignore, README.md
```

`.gitignore`: `venv/`, `db.sqlite3`, `media/`, `staticfiles/`, `.env`, `__pycache__/`, `*.pyc`.

`.env.example`:

```
SECRET_KEY=change-me
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=
DATABASE_URL=sqlite:///db.sqlite3
CLOUDINARY_URL=
EMAIL_HOST=
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
ANTHROPIC_API_KEY=
AI_ENABLED=False
AI_MODEL=claude-haiku-5-5
ORS_API_KEY=
```

`pytest.ini`:

```
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py
```

---

## 5. Core code the model must follow

### 5.1 `config/settings.py` (key parts)

```python
import os
from pathlib import Path
import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ["SECRET_KEY"]
DEBUG = os.getenv("DEBUG", "False") == "True"
ALLOWED_HOSTS = [h for h in os.getenv("ALLOWED_HOSTS", "127.0.0.1,localhost").split(",") if h]
CSRF_TRUSTED_ORIGINS = [o for o in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

INSTALLED_APPS = [
    "django.contrib.admin", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
    "core", "accounts", "reports", "dashboard",
]
AUTH_USER_MODEL = "accounts.User"

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # directly after SecurityMiddleware
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

DATABASES = {"default": dj_database_url.config(default="sqlite:///" + str(BASE_DIR / "db.sqlite3"))}

TIME_ZONE = "Asia/Kolkata"
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
if os.getenv("CLOUDINARY_URL"):
    # Verify compatibility with Django 5.2 at deploy time (Step 11).
    INSTALLED_APPS = ["cloudinary_storage"] + INSTALLED_APPS + ["cloudinary"]
    STORAGES["default"] = {"BACKEND": "cloudinary_storage.storage.MediaCloudinaryStorage"}

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "home"

EMAIL_BACKEND = (
    "django.core.mail.backends.smtp.EmailBackend" if os.getenv("EMAIL_HOST")
    else "django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True

# App constants
BLR_BOUNDS = {"lat_min": 12.7, "lat_max": 13.2, "lon_min": 77.3, "lon_max": 77.9}
MAX_UPLOAD_MB = 5
MAX_PHOTOS_PER_REPORT = 3
DUPLICATE_RADIUS_M = 50
EXIF_MAX_DISTANCE_M = 100
EXIF_MAX_AGE_HOURS = 48
AUTO_CLOSE_DAYS = 7

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
```

Also add the standard `TEMPLATES` block with `DIRS = [BASE_DIR / "templates"]` and the context processor `reports.context.unread_notifications` (Step 9).

### 5.2 Models

`core/models.py`

```python
from django.db import models

class Ward(models.Model):
    name = models.CharField(max_length=120, unique=True)
    zone = models.CharField(max_length=80)
    centroid_lat = models.FloatField()
    centroid_lon = models.FloatField()
    def __str__(self): return self.name

class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)
    sla_days = models.PositiveSmallIntegerField(default=7)
    base_severity = models.PositiveSmallIntegerField(default=2)  # 1..3
    class Meta: verbose_name_plural = "categories"
    def __str__(self): return self.name

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
    class Meta: indexes = [models.Index(fields=["lat", "lon"])]
```

`accounts/models.py`

```python
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
```

Superusers created with `createsuperuser` must get `role=ADMIN` (override `save()` or set in admin).

`reports/models.py`

```python
from django.conf import settings
from django.db import models

class Report(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "SUBMITTED"
        ACKNOWLEDGED = "ACKNOWLEDGED"
        IN_PROGRESS = "IN_PROGRESS"
        RESOLVED = "RESOLVED"
        CLOSED = "CLOSED"
        REOPENED = "REOPENED"
        REJECTED = "REJECTED"

    tracking_id = models.CharField(max_length=20, unique=True, null=True, blank=True)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="reports")
    category = models.ForeignKey("core.Category", on_delete=models.PROTECT)
    description = models.TextField(blank=True)
    landmark = models.CharField(max_length=200, blank=True)
    lat = models.FloatField()
    lon = models.FloatField()
    ward = models.ForeignKey("core.Ward", null=True, on_delete=models.SET_NULL, related_name="reports")
    severity = models.PositiveSmallIntegerField(default=2)
    affects_wheelchair = models.BooleanField(default=False)
    affects_visually_impaired = models.BooleanField(default=False)
    affects_elderly = models.BooleanField(default=False)
    affects_children = models.BooleanField(default=False)
    status = models.CharField(max_length=14, choices=Status.choices, default=Status.SUBMITTED, db_index=True)
    priority_score = models.FloatField(default=0, db_index=True)
    trust_score = models.PositiveSmallIntegerField(default=0)
    exif_ok = models.BooleanField(default=False)
    ai_label = models.CharField(max_length=80, blank=True)
    ai_confidence = models.FloatField(null=True, blank=True)
    duplicate_of = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="duplicates")
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_reports")
    created_at = models.DateTimeField(auto_now_add=True)
    sla_due_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    escalated = models.BooleanField(default=False)

    OPEN_STATUSES = ["SUBMITTED", "ACKNOWLEDGED", "IN_PROGRESS", "REOPENED"]

class ReportPhoto(models.Model):
    class Kind(models.TextChoices):
        BEFORE = "BEFORE"
        AFTER = "AFTER"
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField(upload_to="reports/%Y/%m/")
    kind = models.CharField(max_length=6, choices=Kind.choices, default=Kind.BEFORE)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    uploaded_at = models.DateTimeField(auto_now_add=True)

class StatusHistory(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="history")
    from_status = models.CharField(max_length=14, blank=True)
    to_status = models.CharField(max_length=14)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    remark = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["created_at"]

class Confirmation(models.Model):
    class Kind(models.TextChoices):
        STILL_THERE = "STILL_THERE"
        FIXED = "FIXED"
        NOT_FIXED = "NOT_FIXED"
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name="confirmations")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    kind = models.CharField(max_length=12, choices=Kind.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = ("report", "user", "kind")

class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    report = models.ForeignKey(Report, null=True, on_delete=models.CASCADE)
    message = models.CharField(max_length=250)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta: ordering = ["-created_at"]
```

### 5.3 `reports/geo.py`

```python
from math import radians, sin, cos, asin, sqrt, degrees

def haversine_m(lat1, lon1, lat2, lon2) -> float:
    R = 6371000.0
    p1, p2 = radians(lat1), radians(lat2)
    dphi, dl = p2 - p1, radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * R * asin(sqrt(a))

def bbox(lat, lon, meters):
    """Return (lat_min, lat_max, lon_min, lon_max) around a point for DB prefiltering."""
    dlat = meters / 111_000.0
    dlon = meters / (111_000.0 * max(cos(radians(lat)), 0.01))
    return lat - dlat, lat + dlat, lon - dlon, lon + dlon

def nearest_ward(lat, lon):
    from core.models import Ward
    best, best_d = None, float("inf")
    for w in Ward.objects.all():
        d = haversine_m(lat, lon, w.centroid_lat, w.centroid_lon)
        if d < best_d:
            best, best_d = w, d
    return best
```

### 5.4 `reports/images.py` (validate, read EXIF, re-encode)

```python
import io, uuid
from datetime import datetime
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, ImageOps

ALLOWED = {"JPEG", "PNG", "WEBP"}

def _dms(v, ref):
    d = float(v[0]) + float(v[1]) / 60 + float(v[2]) / 3600
    return -d if ref in ("S", "W") else d

def read_exif(img):
    """Return (lat, lon, taken_datetime) or Nones. Never raises."""
    try:
        exif = img.getexif()
        gps = exif.get_ifd(0x8825)
        lat = lon = None
        if gps and 2 in gps and 4 in gps:
            lat = _dms(gps[2], gps.get(1, "N"))
            lon = _dms(gps[4], gps.get(3, "E"))
        raw = exif.get_ifd(0x8769).get(36867) or exif.get(306)
        taken = datetime.strptime(str(raw), "%Y:%m:%d %H:%M:%S") if raw else None
        return lat, lon, taken
    except Exception:
        return None, None, None

def process_upload(uploaded, max_mb=5):
    """Validate an uploaded image. Return (ContentFile jpeg, exif_tuple). Raises ValidationError."""
    if uploaded.size > max_mb * 1024 * 1024:
        raise ValidationError(f"Image must be under {max_mb} MB.")
    try:
        img = Image.open(uploaded)
        img.verify()
        uploaded.seek(0)
        img = Image.open(uploaded)
    except Exception:
        raise ValidationError("Unsupported or corrupt image. Use JPG, PNG or WebP (not HEIC).")
    if img.format not in ALLOWED:
        raise ValidationError("Only JPG, PNG or WebP images are allowed.")
    exif = read_exif(img)
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((1600, 1600))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)      # re-encoding strips EXIF
    return ContentFile(buf.getvalue(), name=f"{uuid.uuid4().hex}.jpg"), exif
```

### 5.5 `reports/services.py` (single source of business logic)

Required public functions (implement all, with the exact behaviour below):

```python
ALLOWED_TRANSITIONS = {
    "SUBMITTED":    {"ACKNOWLEDGED", "REJECTED"},
    "ACKNOWLEDGED": {"IN_PROGRESS", "REJECTED"},
    "IN_PROGRESS":  {"RESOLVED"},
    "RESOLVED":     {"CLOSED", "REOPENED"},
    "REOPENED":     {"IN_PROGRESS"},
    "CLOSED": set(), "REJECTED": set(),
}

class InvalidTransition(Exception): ...

@transaction.atomic
def create_report(*, reporter, category, lat, lon, description, landmark, severity,
                  affects, processed_photos, exif_results, force_duplicate_of=None) -> Report:
    """
    1. Create Report (ward = nearest_ward, sla_due_at = now + category.sla_days).
    2. Set tracking_id = f"PW-{year}-{pk:06d}" and save again.
    3. Save each ReportPhoto (kind BEFORE).
    4. exif_ok = any photo with GPS within EXIF_MAX_DISTANCE_M of pin AND taken within EXIF_MAX_AGE_HOURS.
    5. duplicate_of = force_duplicate_of.
    6. priority_score = compute_priority(report); trust_score = compute_trust(report).
    7. First StatusHistory row (from "", to SUBMITTED, remark "Report submitted").
    8. Notify ward officers: "New report PW-... in your ward".
    """

def find_duplicates(lat, lon, category_id):
    """Open reports, same category, within DUPLICATE_RADIUS_M (bbox prefilter then haversine)."""

@transaction.atomic
def change_status(report, new_status, user, remark="") -> Report:
    """
    - Raise InvalidTransition if new_status not in ALLOWED_TRANSITIONS[report.status].
    - RESOLVED requires an AFTER photo and a remark (raise ValueError otherwise).
    - REJECTED requires a remark.
    - Set resolved_at / closed_at timestamps.
    - Write StatusHistory. Create Notification for the reporter. Try to send email (try/except).
    """

def can_change_status(user, report) -> bool:
    """ADMIN: always. SUPERVISOR: report.ward.zone == user.zone. OFFICER: report.ward_id == user.ward_id."""

def compute_priority(report) -> float:
    """
    score = base_severity*10  (use report.severity)
          + 15 if school POI within 300 m
          + 15 if hospital POI within 300 m
          + 10 if bus_stop or metro POI within 200 m
          + 5 per ticked affects_* box
          + min(2 * number of STILL_THERE confirmations, 10)
          + min(days_open, 15)
    """

def compute_trust(report) -> int:
    """
    exif_ok 30 + (fresh timestamp portion included in exif_ok) ... implement as:
    +30 if GPS matches, +20 if timestamp fresh, +20 if ai_label == category name,
    +min(5 * confirmations, 20), +10 if reporter has a previous CLOSED report. Cap at 100.
    Store exif_gps_ok and exif_time_ok separately if needed (extra BooleanFields).
    """

def notify(user, report, message): ...
def ward_scores(): ...   # reliability and accessibility scores per ward (Step 13 and 14)
```

### 5.6 `accounts/permissions.py`

```python
from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

def role_required(*roles):
    def deco(view):
        @wraps(view)
        def wrapper(request, *a, **kw):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.role not in roles:
                raise PermissionDenied
            return view(request, *a, **kw)
        return wrapper
    return deco
```

Provide a custom `templates/403.html`.

### 5.7 `reports/ai.py` (optional feature, must fail safe)

```python
import base64, json, os
import anthropic
from core.models import Category

SYSTEM = ("You classify photos of blocked footpaths. Reply with JSON only, no markdown: "
          '{"is_obstruction": true/false, "category": "<one of the allowed names>", '
          '"severity": 1-3, "confidence": 0-1}')

def suggest_from_image(jpeg_bytes: bytes):
    if os.getenv("AI_ENABLED", "False") != "True":
        return None
    try:
        names = list(Category.objects.values_list("name", flat=True))
        client = anthropic.Anthropic(timeout=10.0)   # reads ANTHROPIC_API_KEY
        msg = client.messages.create(
            model=os.getenv("AI_MODEL", "claude-haiku-5-5"),
            max_tokens=200, system=SYSTEM + " Allowed categories: " + ", ".join(names),
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.b64encode(jpeg_bytes).decode()}},
                {"type": "text", "text": "Classify this image."}]}])
        text = "".join(b.text for b in msg.content if b.type == "text").strip()
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        data = json.loads(text)
        if data.get("category") not in names:
            return None
        return data
    except Exception:
        return None
```

---

## 6. URL map

| URL | View | Who |
|---|---|---|
| `/` | home (hero, stats, report button) | all |
| `/accounts/register/`, `/login/`, `/logout/`, `/profile/` | auth | per page |
| `/report/new/` | submit report | logged in |
| `/report/check-duplicates/` | JSON: nearby similar reports | logged in |
| `/my/` | my reports | logged in |
| `/r/<tracking_id>/` | report detail (public view redacts reporter; owner and staff see more) | all |
| `/track/` | lookup by tracking ID | all |
| `/r/<id>/confirm/` | STILL_THERE confirmation | logged in |
| `/r/<id>/feedback/` | FIXED or NOT_FIXED | reporter only |
| `/officer/` | work queue | OFFICER, SUPERVISOR, ADMIN |
| `/officer/r/<id>/` | manage report (status form, after photo) | same, with object check |
| `/notifications/` | list and mark read | logged in |
| `/dashboard/` | public dashboard page | all |
| `/api/stats/summary/`, `/weekly/`, `/wards/`, `/markers/` | JSON for charts and map | all (no personal data) |
| `/api/suggest/` | POST image, returns AI suggestion | logged in |
| `/route-check/` | accessible route page (Step 16) | all |
| `/admin/` | Django admin | ADMIN |

Templates required: `base.html`, `home.html`, `accounts/{login,register,profile}.html`, `reports/{new,detail,my,track}.html`, `officer/{queue,manage}.html`, `dashboard/dashboard.html`, `notifications.html`, `403.html`, `404.html`.

---

## 7. Seed data

`core/management/commands/seed_demo.py` must be **idempotent** (safe to run twice). Create:

- 6 wards (approximate placeholder centroids, replace with real ward data later): Koramangala (12.9352, 77.6245), Indiranagar (12.9784, 77.6408), Jayanagar (12.9308, 77.5838), Malleshwaram (13.0035, 77.5646), Whitefield (12.9698, 77.7500), Yelahanka (13.1007, 77.5963). Zones: group them into 2 or 3 zones.
- Categories with SLA days: Illegal Parking 2, Garbage Dumping 3, Vendor Encroachment 5, Construction Debris 7, Others 7, Broken Pavement 14. Base severity 1 to 3 as sensible.
- Users (password `demo12345`): `citizen1`, `citizen2`, one officer per ward (`officer_koramangala`, etc.), `supervisor1`, `admin1` (role ADMIN, is_staff, is_superuser).
- About 30 POIs near the wards (schools, hospitals, bus stops, metro) and about 60 reports over the past 8 weeks in mixed statuses, with realistic timestamps, some overdue and some escalated. Use a small generated placeholder image for photos (create with Pillow).

---

## 8. Step-by-step implementation

Each step lists **Files**, **Tasks**, **Checks** and **Done when**. Follow in order.

### STEP 1: Skeleton and environment
**Files:** `config/*`, apps (`core`, `accounts`, `reports`, `dashboard`), `.gitignore`, `.env.example`, `requirements.txt`, `pytest.ini`, `templates/base.html`, `README.md` stub.
**Tasks:** create project per Sections 3 to 5.1. Define the `User` model (5.2) **before** first migrate. Move old `app.py` to `legacy/`.
**Checks:** `python manage.py check`, `python manage.py makemigrations`, `python manage.py migrate`, `python manage.py runserver`.
**Done when:** migrate succeeds and the site loads at `/` with Bootstrap styling.

### STEP 2: Models and admin registration
**Files:** all `models.py`, all `admin.py`.
**Tasks:** implement every model in 5.2, register in admin with `list_display`, `list_filter`, `search_fields`. Make superuser get role ADMIN.
**Checks:** `makemigrations --check`, `migrate`.
**Done when:** you can create a Ward, Category and Report in `/admin/`.

### STEP 3: Authentication and roles
**Files:** `accounts/{forms,views,urls,permissions}.py`, auth templates, `templates/403.html`, navbar in `base.html`.
**Tasks:** registration (always CITIZEN, fields: username, email, phone, password), login, logout, profile. `role_required` decorator. Navbar links by role.
**Tests (`tests/test_permissions.py`):** citizen gets 403 on `/officer/`; anonymous is redirected to login; officer of Ward A gets 403/404 on a Ward B report.
**Done when:** tests pass.

### STEP 4: Report submission
**Files:** `reports/{forms,views,urls,images,geo,services}.py`, `templates/reports/new.html`, `static/js/report_map.js`.
**Tasks:**
- Form with up to 3 photos (use a multiple-file input and handle `request.FILES.getlist("photos")` manually), category, severity (1 to 3), affects checkboxes, description, landmark, hidden `lat`/`lon`.
- Leaflet map centred on Bengaluru; click places a marker and fills hidden fields; "Use my location" button via `navigator.geolocation`.
- Server validation: bounds from `BLR_BOUNDS`, 1 to 3 photos, `process_upload` per image.
- `create_report()` per 5.5 (duplicate and EXIF parts can be stubs now).
**Tests:** `test_geo.py` (haversine known distance, nearest ward), `test_images.py` (reject oversized, reject non-image, accept JPEG and strip EXIF).
**Done when:** a logged-in citizen submits a report with photo and pin and lands on the detail page showing the tracking ID.

### STEP 5: Tracking pages
**Files:** `reports/views.py`, templates `my.html`, `detail.html`, `track.html`.
**Tasks:** My Reports with status badges, detail page with timeline from `StatusHistory` and photos, public lookup by tracking ID. Public view hides the reporter entirely.
**Tests:** public detail page response does not contain reporter username or email.
**Done when:** tracking works while logged out.

### STEP 6: Officer workflow
**Files:** `reports/services.py` (`change_status`, `can_change_status`), `reports/views.py`, `templates/officer/*`.
**Tasks:** queue page (officer locked to own ward; supervisor by zone; admin all), filters (category, status, overdue), sort by `-priority_score`, then `created_at`. Manage page with status form (only valid next statuses shown), after-photo upload (kind AFTER, processed with `process_upload`), remark. Supervisors can reassign `assigned_to`.
**Tests:** every valid transition passes; invalid ones (e.g. SUBMITTED to CLOSED) raise `InvalidTransition`; RESOLVED without AFTER photo fails.
**Done when:** tests pass and the flow works in the browser.

### STEP 7: Admin panel polish
**Files:** `*/admin.py`.
**Tasks:** editable `sla_days` and `base_severity` on Category, `StatusHistory` read-only inline on Report, CSV export action, user admin shows role, ward, zone.
**Done when:** an admin can create an officer and export reports.

### STEP 8: Public dashboard
**Files:** `dashboard/views.py`, `dashboard/urls.py`, `templates/dashboard/dashboard.html`, `static/js/dashboard.js`.
**Tasks:** JSON endpoints (using ORM `aggregate`, `annotate`, `TruncWeek`), cached 60 s with `cache_page`. Page shows KPI cards (total, open, resolved, average days to resolve, resolution rate), clustered marker map coloured by status, weekly line chart by category, reports-per-ward bar chart, ward leaderboard table. Filters: date range, category, ward. JSON must contain no personal data.
**Tests:** summary endpoint counts equal ORM counts.
**Done when:** dashboard numbers match admin.

### STEP 9: Notifications
**Files:** `reports/context.py`, `templates/notifications.html`, navbar bell.
**Tasks:** `notify()` called inside `change_status()` and `create_report()`. Bell shows unread count; list page marks read. Email sent in `try/except`.
**Done when:** citizen sees a notification after an officer acknowledges.

### STEP 10: Seed data and tests
**Files:** `core/management/commands/seed_demo.py` (Section 7), more tests.
**Done when:** `python manage.py seed_demo` fills the dashboard and `pytest` passes fully.

### STEP 11: Deploy MVP
**Tasks:**
- Render web service. Build: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`. Start: `gunicorn config.wsgi`.
- Env vars per Section 4 and `.env.example`. `DEBUG=False`, `ALLOWED_HOSTS` and `CSRF_TRUSTED_ORIGINS` set to the Render URL (`https://...`).
- Neon or Supabase PostgreSQL via `DATABASE_URL`. Cloudinary via `CLOUDINARY_URL`.
- Run `seed_demo` once through the Render shell.
**Done when:** the live site works end to end and an uploaded image survives a redeploy. If Cloudinary storage conflicts with Django 5.2, report the exact error and propose a persistent-disk fallback.

### STEP 12: Verified reports
**Files:** `reports/services.py`, `reports/views.py`, `new.html`, `detail.html`.
**Tasks:**
- Wire EXIF results into `exif_ok` and `trust_score` (`compute_trust`).
- `find_duplicates()`; JSON endpoint `/report/check-duplicates/`; the form shows a warning with a "Confirm that one instead" link; "Submit anyway" sets `duplicate_of`.
- "Still there" button (one per user per report via `Confirmation`), which recalculates priority and trust.
- Show a Verified badge when `trust_score >= 50` (officer view and detail page).
**Tests:** photo without EXIF gives lower trust; duplicate within 50 m of same category is found; one at 200 m is not.

### STEP 13: SLA, escalation and closure
**Files:** `reports/management/commands/{escalate_overdue,auto_close}.py`, `services.py`, templates.
**Tasks:**
- Show countdown or "Overdue by N days" for open reports.
- `escalate_overdue`: for open reports with `sla_due_at < now` and `escalated=False`, set `escalated=True`, notify officer and supervisor, add a `StatusHistory` remark "Auto-escalated" (same status to same status entry allowed only for this remark, implement as a direct history insert, not via `change_status`).
- Citizen feedback on RESOLVED reports: FIXED calls `change_status(..., CLOSED)`, NOT_FIXED calls `change_status(..., REOPENED)`.
- `auto_close`: RESOLVED reports older than `AUTO_CLOSE_DAYS` with no feedback become CLOSED.
- `ward_scores()`: `reliability = 70 * on_time_resolved_share + 30 * (1 - overdue_open_share)` (guard divide by zero). Show on leaderboard.
**Tests:** overdue report gets escalated exactly once; NOT_FIXED reopens.

### STEP 14: Accessibility-aware priority (headline feature)
**Files:** `core/management/commands/load_pois.py`, `data/pois.json`, `services.py`, templates.
**Tasks:**
- `load_pois` reads `data/pois.json` (list of `{name, type, lat, lon}`) and upserts. The app must never call a live map API for POIs.
- `compute_priority()` exactly as in 5.5; recalculate on create, on confirmation, and daily in a command `recalc_priority`.
- `accessibility_score(ward) = 100 * (1 - ward_open_priority_sum / max_ward_open_priority_sum)`, 100 if max is 0. Show on dashboard.
- Detail page shows affected-group chips and "Near: school (120 m)".
**Tests:** identical report near a school has higher priority than one far away.

### STEP 15: AI photo assistant (optional)
**Files:** `reports/ai.py`, `reports/views.py` (`/api/suggest/`), `report_map.js`.
**Tasks:** when the user picks a photo, POST a resized copy to `/api/suggest/`; pre-fill category and severity if a suggestion returns; show "AI suggestion, please confirm". Store `ai_label` and `ai_confidence` on submit. `AI_ENABLED=False` or any failure means the form behaves exactly as before.
**Tests:** with AI disabled, the endpoint returns `{"suggestion": null}` and submission still works.

### STEP 16: Accessible route check (stretch)
**Files:** `reports/routing.py`, view, template `route_check.html`.
**Tasks:** user picks start and end on a Leaflet map. Server calls OpenRouteService `foot-walking` directions in GeoJSON format with `ORS_API_KEY`, timeout 10 s. Sample points along the line every ~10 m, list open reports within 15 m of any sample. Draw route and blockage markers. On any failure show a friendly message.
**Tests:** unit-test the "reports within 15 m of a polyline" function with a hand-made line.

### STEP 17: Polish and documentation
**Tasks:** README (problem, features, screenshots placeholder, setup, demo logins, deploy notes), mobile responsiveness, empty states, flash messages, 404 page, favicon, accessibility basics (labels, alt text, contrast).
**Done when:** a new developer can clone, follow the README and run the site in under 10 minutes.

---

## 9. Security checklist (verify at the end)

- [ ] Every view has `role_required` or `login_required` plus an object-level check.
- [ ] Public pages and `/api/stats/*` contain no reporter name, phone or email.
- [ ] Uploads are re-encoded with Pillow; originals are never stored.
- [ ] `DEBUG=False`, secure cookies and SSL redirect on in production.
- [ ] No secret committed; `.env` ignored.
- [ ] Login and report submission rate-limited (simple per-user daily cap of reports, for example 20, enforced in `create_report`).
- [ ] CSRF tokens on all forms.

## 10. Known pitfalls

| Problem | Rule |
|---|---|
| Custom user model after first migrate | Set it in Step 1. If broken, delete `db.sqlite3` and migration files, regenerate. |
| Images vanish on redeploy | Cloudinary or persistent disk; test in Step 11. |
| CSRF 403 on live site | Set `CSRF_TRUSTED_ORIGINS` with `https://`. |
| Missing CSS in production | `collectstatic` in build command, WhiteNoise in middleware. |
| iPhone HEIC upload fails | Reject with a clear message, accept JPEG, PNG, WebP only. |
| Slow dashboard | Aggregate queries, `select_related`, 60 s cache. |
| Free-tier server asleep during demo | Open the site a few minutes before presenting. |
| AI or email failure | Always `try/except`, never block saving. |

## 11. Definition of done (whole project)

1. `pytest` passes; `python manage.py check --deploy` shows no critical warnings.
2. Seeded demo shows: full dashboard, an escalated overdue report, a verified report, a high-priority report near a school.
3. A citizen can report, track and confirm closure; an officer can work a queue and resolve with an after photo; an admin can manage users, wards and SLAs.
4. Live URL deployed with persistent images and a working database.
5. README with demo logins and screenshots.
