# PaveWatch

PaveWatch is a Django platform for reporting and tracking footpath obstructions with photo and map pin verification, controlled municipal workflow resolution, and public accountability dashboards.

## Technology Stack
- **Backend:** Django 5.2 LTS, Python 3.12+
- **Frontend:** Bootstrap 5.3.3, Vanilla JavaScript, Leaflet 1.9.4, Chart.js 4.4.x
- **Database:** SQLite (local development), PostgreSQL (production)
- **Image Processing:** Pillow (stripping EXIF for privacy, resizing)

## Getting Started
1. Create virtual environment:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Set environment variables:
   Copy `.env.example` to `.env`.
4. Apply migrations:
   ```bash
   python manage.py migrate
   ```
5. Run development server:
   ```bash
   python manage.py runserver
   ```
