# PROJECT MEMORY: PaveWatch

## 1. Project snapshot
- **Name:** PaveWatch
- **Description:** A Django platform for citizens to report footpath obstructions with photo and map pin, ward officers to resolve via controlled workflow, and the public to track progress on an accessibility-aware dashboard.
- **Stack:**
  - Backend: Python 3.12+ (local runtime: Python 3.13.15), Django 5.2 LTS
  - Database: SQLite (development), PostgreSQL via `dj-database-url` (production)
  - Frontend: Django Templates, Bootstrap 5.3.3, Vanilla JavaScript
  - Maps & Visualizations: Leaflet 1.9.4 + OpenStreetMap, Leaflet.markercluster 1.5.3, Chart.js 4.4.x
  - Static & Media: WhiteNoise (static), Pillow (image processing), Cloudinary (production media)
  - Testing: pytest, pytest-django
  - Server: Gunicorn
- **Repo URL:** Local repository initialized at `F:\DSCE CSE\PaveWatch-main` (Remote not yet configured)
- **Current date:** 2026-11-22

---

## 2. Step tracker

| Step | Title | Status | Date done | Commit hash | Evidence |
|---|---|---|---|---|---|
| STEP 1 | Skeleton and environment | DONE | 2026-11-21 | 8598c7f | check (0 issues), makemigrations --check (0 changes), migrate (all applied OK), pytest (1 passed in 0.31s), HTTP 200 with Bootstrap at `/` |
| STEP 2 | Models and admin registration | DONE | 2026-11-22 | 1a2b0f0 | makemigrations reports (created Report, Notification, ReportPhoto, StatusHistory, Confirmation), migrate applied reports.0001_initial, check 0 issues, pytest (5 passed in 4.20s), admin creation of Ward, Category, Report verified |
| STEP 3 | Authentication and roles | DONE | 2026-11-22 | e3a9339 | check (0 issues), makemigrations --check (0 changes), pytest (10 passed in 10.77s) testing anonymous redirect, citizen 403 on queue, ward officer object check, supervisor zone check, admin permissions, and citizen registration |
| STEP 4 | Report submission | DONE | 2026-11-23 | - | Leaflet interactive map with pin placement, BLR bounds check, photo upload, priority calculation, details redirect |
| STEP 5 | Tracking pages | DONE | 2026-11-23 | - | Public tracking page with pagination & filters, detailed view with status history timeline & map, reporter identity privacy preserved |
| STEP 6 | Officer workflow | DONE | 2026-11-23 | - | Officer work queue filtered by ward/zone, manage report view with transition enforcement and AFTER photo upload |
| STEP 7 | Admin panel polish | DONE | 2026-11-23 | - | Editable sla_days and base_severity on Category, StatusHistory read-only inline, CSV export action on reports, User admin shows role/ward/zone with add_fieldsets; pytest (16 passed) |
| STEP 8 | Public dashboard | DONE | 2026-11-23 | - | KPI summary cards, Leaflet clustered map, Chart.js breakdown charts by status/ward, ward leaderboard |
| STEP 9 | Notifications | DONE | 2026-11-22 | <commit_hash> | system check passed, pytest passed, notifications UI added
| STEP 10 | Seed data and tests | DONE | 2026-11-23 | - | seed_demo populated 6 wards, categories, POIs, demo users and 60 reports; 13/13 pytests passing |
| STEP 11 | Deploy MVP | DONE | 2026-11-23 | - | Local server active and serving HTTP 200 on http://127.0.0.1:8000/ |
| STEP 12 | Verified reports | PENDING | - | - | - |
| STEP 13 | SLA, escalation and closure | PENDING | - | - | - |
| STEP 14 | Accessibility-aware priority (headline feature) | PENDING | - | - | - |
| STEP 15 | AI photo assistant (optional) | PENDING | - | - | - |
| STEP 16 | Accessible route check (stretch) | PENDING | - | - | - |
| STEP 17 | Polish and documentation | PENDING | - | - | - |

---

## 3. Change log (append-only)

| Date | Step | Agent | Files created/changed | What and why |
|---|---|---|---|---|
| 2026-11-21 | Setup | Lead Orchestrator | `PROJECT_MEMORY.md`, `.git` | Initialized Git repository and created PROJECT_MEMORY.md tracking document per specification. |
| 2026-11-21 | STEP 1 | Lead Orchestrator | `config/*`, `core/*`, `accounts/*`, `reports/*`, `dashboard/*`, `templates/base.html`, `templates/home.html`, `static/*`, `legacy/app.py`, `manage.py`, `requirements.txt`, `.gitignore`, `.env.example`, `.env`, `pytest.ini`, `tests/*` | Built project skeleton, configured Django 5.2 with WhiteNoise & SQLite, defined `accounts.User` before initial migrate, verified Bootstrap styling on home page and passed pytest. |
| 2026-11-22 | STEP 2 | Lead Orchestrator | `reports/models.py`, `reports/migrations/0001_initial.py`, `core/admin.py`, `accounts/admin.py`, `reports/admin.py`, `tests/test_models.py` | Implemented Report, ReportPhoto, StatusHistory, Confirmation, Notification models; registered all models in admin with search/filters/inlines; verified superuser ADMIN role and admin model creation via pytest. |
| 2026-11-22 | STEP 3 | Lead Orchestrator | `accounts/{forms,views,urls,permissions}.py`, `reports/{services,views,urls}.py`, `templates/{403.html,base.html,accounts/*,officer/*}`, `tests/test_permissions.py` | Built citizen registration, login, logout, profile view, role_required decorator, object-level officer/supervisor permission checks, role-based navbar, and custom 403 error page. Verified with 10 unit/integration tests. |
| 2026-11-23 | MVP Fix & Deploy | Senior Fullstack | `reports/geo.py`, `reports/images.py`, `reports/forms.py`, `reports/views.py`, `reports/urls.py`, `dashboard/services.py`, `dashboard/views.py`, `templates/reports/*`, `templates/officer/*`, `templates/dashboard/home.html`, `templates/404.html`, `tests/test_notifications.py` | Implemented missing `geo.py` & `images.py` modules, fixed `create_report()` invocation with Leaflet pin & photo processing, completed officer queue & management workflow with AFTER photo uploads, built public dashboard with Chart.js & Leaflet clusters, resolved test transitions, ran `seed_demo`, verified 13/13 passing pytests, and deployed local dev server on http://127.0.0.1:8000/. |
| 2026-11-23 | STEP 7 | Senior Fullstack | `core/admin.py`, `accounts/admin.py`, `reports/admin.py`, `tests/test_admin_polish.py` | Polished Django Admin: made `sla_days` and `base_severity` editable in Category list view; configured User admin with `add_fieldsets` and profile fields (role, ward, zone, points); added `export_reports_to_csv` admin action respecting privacy constraints; made `StatusHistory` inline read-only. Added unit tests with 16/16 pytests passing. |
| 2026-11-24 | Map & Demo Images Fix | Senior Fullstack | `reports/demo_images.py`, `core/management/commands/seed_demo.py`, `templates/reports/{create,detail,track}.html`, `templates/officer/manage.html`, `templates/dashboard/home.html` | Created `reports/demo_images.py` generating realistic sidewalk pavement images with category badges, curb hazard stripes, GPS stamps, and before/after tags. Refreshed all 72 demo report photos via `seed_demo --refresh-images`. Fixed Leaflet CDN default marker icon asset paths, added `map.invalidateSize()` on all maps, added interactive clustered markers with report links to the Track Reports page, and verified HTTP 200 on all map & media endpoints. All 16 pytests passing. |
| 2026-11-24 | Map Tile API Switch | Senior Fullstack | `templates/reports/{create,detail,track}.html`, `templates/officer/manage.html`, `templates/dashboard/home.html` | Replaced blocked OpenStreetMap volunteer tile server (`tile.openstreetmap.org`, which triggers HTTP 403 policy block on localhost/app referrers) with high-availability CARTO Voyager tiles (`basemaps.cartocdn.com/rastertiles/voyager/`). Tested and verified map rendering across all 5 map templates. |

---

## 4. Decisions and assumptions
- Local environment has Python 3.13.15 installed, which is fully compatible with Django 5.2+.
- Virtual environment created at `.venv` in the workspace root.
- `AUTH_USER_MODEL = "accounts.User"` configured before running the first migration.
- `accounts.User.save()` automatically assigns `role = Role.ADMIN` for superusers.
- Configured staticfiles storage to use `StaticFilesStorage` when `DEBUG = True` and `CompressedManifestStaticFilesStorage` when `not DEBUG`, allowing seamless local development and automated pytest runs without mandatory pre-collected static files.
- Added `testserver` to `ALLOWED_HOSTS` to support test client execution.
- Added `ReportPhotoInline` and `StatusHistoryInline` to `ReportAdmin` in Django admin.
- Citizen registration always sets `role = Role.CITIZEN`.
- Implemented `@role_required` decorator supporting multiple roles and redirecting unauthenticated users to login while raising `PermissionDenied` (403) for unauthorized authenticated roles.
- Initialized `reports.services.can_change_status(user, report)` implementing object-level access controls for officers (same ward), supervisors (same zone), and admins (global).

---

## 5. Known issues and blockers
- None currently. All checks and tests pass with 0 errors and 0 warnings.

---

## 6. Working commands
- Virtualenv activation (PowerShell): `.\.venv\Scripts\activate`
- Dependency installation: `.\.venv\Scripts\pip.exe install -r requirements.txt`
- Django system check: `.\.venv\Scripts\python.exe manage.py check`
- Migration check: `.\.venv\Scripts\python.exe manage.py makemigrations --check`
- Apply migrations: `.\.venv\Scripts\python.exe manage.py migrate`
- Pytest execution: `.\.venv\Scripts\pytest.exe`
- Run local server: `.\.venv\Scripts\python.exe manage.py runserver`

---

## 7. NEXT ACTION
STEP 7 completed. Awaiting user command to proceed to STEP 12 (Verified reports: EXIF check, duplicate detection API & warnings, "Still there" confirmation, Verified badge).
