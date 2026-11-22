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
| STEP 4 | Report submission | IN_PROGRESS | - | - | - |
| STEP 5 | Tracking pages | PENDING | - | - | - |
| STEP 6 | Officer workflow | PENDING | - | - | - |
| STEP 7 | Admin panel polish | PENDING | - | - | - |
| STEP 8 | Public dashboard | PENDING | - | - | - |
| STEP 9 | Notifications | PENDING | - | - | - |
| STEP 10 | Seed data and tests | PENDING | - | - | - |
| STEP 11 | Deploy MVP | PENDING | - | - | - |
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
Awaiting user command 'next' to begin STEP 4 (Report submission).
