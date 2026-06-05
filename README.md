# Financial Dashboards

This branch starts the migration from static HTML dashboards to a Django/Postgres application with controlled workbook uploads through Django Admin.

## Current Backend Slice

- Django project scaffold in `config/`
- Postgres-ready settings with secure production defaults
- Dashboard, metric, import, market share, regulatory fee, and audit models
- Django Admin registration
- Admin upload entry point for workbook imports
- First server-side importer for the BWA/Telesol dashboard
- Email/TOTP-capable 2FA dependency configuration
- Architecture and security handoff docs in `docs/`

## Local Setup

Python 3.12 is required for the Django 6.x dependency line.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_reference_data
python manage.py createsuperuser
python manage.py runserver
```

The default settings expect Postgres. For quick local syntax checks without Postgres, set:

```bash
DATABASE_ENGINE=sqlite
```

## Admin Upload Flow

1. Sign in to `/admin/`.
2. Run `python manage.py seed_reference_data` first so categories, companies, and metrics exist.
3. Open `Workbook imports`.
4. Use the `Upload workbook` admin action link.
5. Select `BWA` and upload an `.xlsx` workbook with year-named sheets.

Only BWA parsing is implemented in this first slice. The remaining dashboards should reuse the same service pattern.
