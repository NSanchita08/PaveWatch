# PaveWatch

**Accessible, Walkable, Accountable Footpaths for Bengaluru.**

PaveWatch is a Django civic-tech platform where citizens report footpath obstructions with photo and map pin verification, municipal ward officers resolve issues through a controlled SLA-tracked workflow, and the public tracks progress on an accessibility-aware dashboard.

---

## The Problem

Blocked footpaths—from illegal parking, construction debris, garbage dumping, and broken pavement—force pedestrians onto busy roads. Wheelchair users, visually impaired citizens, elderly residents, and children face disproportionate risk, yet complaints lack location verification, accessibility context, and transparent SLA accountability.

---

## Features

- **Verified Citizen Reports:** Leaflet pin placement within Bengaluru bounds, Google Maps address/landmark search, Pillow image validation & EXIF stripping, EXIF GPS/timestamp trust scoring (`trust_score >= 50` Verified badge), duplicate detection within 50 m, and `"Still there"` community confirmations.
- **Controlled Officer Workflow:** Role-based access (`CITIZEN`, `OFFICER`, `SUPERVISOR`, `ADMIN`) with strict state transitions (`SUBMITTED → ACKNOWLEDGED → IN_PROGRESS → RESOLVED → CLOSED / REOPENED`), mandatory `AFTER` photo + remark to resolve, and citizen resolution feedback (`FIXED` / `NOT_FIXED`).
- **SLA, Escalation & Reliability:** Category-based SLA deadlines, countdown/overdue badges, automated escalation (`escalate_overdue`), auto-closure (`auto_close`), and ward reliability scores.
- **Accessibility-Aware Priority (Headline Feature):** Offline Bengaluru POI dataset (`data/pois.json` loaded via `load_pois`) boosts priority near schools (+15 within 300 m), hospitals (+15 within 300 m), and bus/metro stops (+10 within 200 m), alongside affected-group chips and ward accessibility scores on the dashboard.
- **Optional AI Photo Assistant:** Fail-safe image pre-classification via `/api/suggest/` (`AI_ENABLED=True` + `ANTHROPIC_API_KEY`) that pre-fills category and severity without ever blocking submission.
- **Accessible Route Check:** Pick Start and Destination on `/route-check/` to fetch a walking route (Google Directions API or OpenRouteService) and highlight open footpath obstructions within 15 m.

---

## Screenshots

> _Add screenshots here after capturing:_
> - `docs/screenshots/home.png` — Landing & tracking lookup
> - `docs/screenshots/dashboard.png` — Public dashboard, clustered map & ward leaderboard
> - `docs/screenshots/report_detail.png` — Report detail with trust score, nearby POIs & timeline
> - `docs/screenshots/route_check.png` — Accessible walking route check

---

## Technology Stack

- **Backend:** Python 3.12+, Django 5.2 LTS, WhiteNoise, Gunicorn
- **Database:** SQLite (development), PostgreSQL via `dj-database-url` (production)
- **Frontend:** Django Templates, Bootstrap 5.3.3, Vanilla JS, Leaflet 1.9.4 + MarkerCluster, Chart.js 4.4.3
- **Images & Storage:** Pillow (re-encoding & EXIF stripping), Cloudinary (production media)
- **Testing:** `pytest`, `pytest-django`

---

## Local Setup (Under 10 Minutes)

1. **Create and activate a virtual environment:**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
2. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
3. **Configure environment variables:**
   Copy `.env.example` to `.env` and set `SECRET_KEY` (any random string for local dev) and `DEBUG=True`.
   Optional keys:
   - `GOOGLE_MAPS_API_KEY` (for `/api/geocode/` address search and `/route-check/` walking directions)
   - `ORS_API_KEY` (OpenRouteService fallback for `/route-check/`)
   - `ANTHROPIC_API_KEY` + `AI_ENABLED=True` (optional AI photo assistant)
4. **Apply migrations and load seed data:**
   ```powershell
   python manage.py migrate
   python manage.py load_pois
   python manage.py seed_demo
   python manage.py recalc_priority
   ```
5. **Run the server:**
   ```powershell
   python manage.py runserver
   ```
   Open http://127.0.0.1:8000/

6. **Run tests & checks:**
   ```powershell
   python manage.py check
   python manage.py makemigrations --check
   pytest
   ```

---

## Demo Logins

All demo accounts created by `seed_demo` use password **`demo12345`**:

| Role | Username | Scope |
|---|---|---|
| Citizen | `citizen1`, `citizen2` | Submit, confirm, and give resolution feedback |
| Ward Officer | `officer_koramangala` (and one per ward) | Manage reports in assigned ward |
| Supervisor | `supervisor1` | Manage & reassign reports in `ZoneA` |
| Admin | `admin1` | Full Django Admin (`/admin/`) & global queue |

---

## Scheduled / Maintenance Commands

```powershell
python manage.py escalate_overdue   # Escalate overdue open reports & notify officers/supervisors
python manage.py auto_close         # Auto-close RESOLVED reports older than AUTO_CLOSE_DAYS
python manage.py recalc_priority    # Recalculate priority scores (days_open + POIs + confirmations)
```

---

## Production Deployment (Render)

- **Build command:**
  ```bash
  pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate && python manage.py load_pois
  ```
- **Start command:**
  ```bash
  gunicorn config.wsgi
  ```
- **Required environment variables:**
  - `SECRET_KEY` (strong random secret)
  - `DEBUG=False`
  - `ALLOWED_HOSTS=your-app.onrender.com`
  - `CSRF_TRUSTED_ORIGINS=https://your-app.onrender.com`
  - `DATABASE_URL` (PostgreSQL connection string)
  - `CLOUDINARY_URL` (for persistent media uploads across redeploys)
