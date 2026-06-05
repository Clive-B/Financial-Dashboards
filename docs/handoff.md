# Financial Dashboards — Developer Handoff

**Last updated:** June 2026  
**Repo:** https://github.com/Clive-B/Financial-Dashboards  
**Stack:** Django 6, SQLite (dev) / PostgreSQL (prod), Chart.js, Two-Factor Auth

---

## What Has Been Built

The six standalone static HTML dashboards have been migrated into a Django application. Each dashboard now:

- Pulls live financial data from an authenticated JSON API backed by a database
- Matches the look, feel, charts, KPI cards, Executive Intelligence section, and notes from the original HTML files exactly
- Can be updated by uploading a revised Excel workbook through Django Admin — no code changes required

### Dashboards available

| Dashboard | Category slug | Company | Data years |
|---|---|---|---|
| BWA | `bwa` | Telesol | 2021–2022 |
| ICH | `ich` | AFRIWAVE | 2021–2024 + 2017–2025 regulatory fees |
| Pay Television | `pay-television` | DSTV | 2020–2024 |
| Tower Infrastructure | `tower-infrastructure` | African Towers | 2022–2024 |
| Mobile Network | `mobile-network` | MTN, Telecel, AT | (upload required) |
| Terrestrial Fibre | `terrestrial-fibre` | Spectrum Fibre | (upload required) |

The embedded figures for BWA, ICH, Pay TV, and Tower Infrastructure were seeded from the original static HTML files. Mobile Network and Terrestrial Fibre need workbook uploads before data appears.

---

## Project Structure

```
Financial Dashboard/
├── config/               # Django project settings
│   ├── settings.py       # Env-variable driven; SQLite or Postgres
│   ├── urls.py           # Root URL config
│   ├── middleware.py     # Security headers + CSP
│   └── wsgi.py
├── dashboards/           # Core app
│   ├── models.py         # DashboardCategory, Company, MetricDefinition,
│   │                     # FinancialPeriod, FinancialValue, WorkbookImport,
│   │                     # RegulatoryFeeValue, ImportChange, MarketShareValue
│   ├── views.py          # dashboard_detail, dashboard_metrics_api, dashboard_fees_api
│   ├── urls.py           # /dashboards/<slug>/, /api/metrics/, /api/fees/
│   ├── admin.py          # WorkbookImport admin with custom upload view
│   └── management/commands/
│       ├── seed_reference_data.py   # Creates categories, companies, metrics
│       └── seed_dashboard_data.py  # Loads embedded HTML figures into DB
├── workbooks/            # Upload and parsing
│   ├── forms.py          # WorkbookUploadForm with magic-byte validation
│   ├── validation.py     # validate_upload(), write_atomically(), ValidationError
│   └── services/
│       └── importer.py   # import_workbook() — routes to BWA/MNO parsers
├── accounts/             # Auth app (placeholder for future user management)
├── templates/
│   ├── base.html         # Shared layout with extra_styles/extra_scripts blocks
│   └── dashboards/
│       ├── index.html    # Dashboard listing page
│       └── detail.html   # Full dashboard — charts, KPIs, insights, table, notes
├── .env                  # Local dev environment variables (not committed)
├── .env.example          # Template for .env
├── requirements.txt
└── manage.py
```

---

## Local Setup (from scratch)

### Prerequisites

- Python 3.12
- Git

### Steps

```bash
# 1. Clone the repo
git clone https://github.com/Clive-B/Financial-Dashboards.git
cd Financial-Dashboards

# 2. Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create a .env file (copy and edit the example)
cp .env.example .env
```

Edit `.env` for local development — the minimal config is:

```env
DJANGO_SECRET_KEY=any-long-random-string-here
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_ENGINE=sqlite

EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
DEFAULT_FROM_EMAIL=admin@example.com
OTP_EMAIL_SENDER=admin@example.com
```

```bash
# 5. Run migrations
python manage.py migrate

# 6. Seed categories, companies, and metric definitions
python manage.py seed_reference_data

# 7. Seed the embedded financial data from the original HTML dashboards
python manage.py seed_dashboard_data

# 8. Create a superuser
python manage.py createsuperuser

# 9. Start the server
python manage.py runserver
```

Open **http://127.0.0.1:8000** in your browser.

---

## Logging In

The app uses **two-factor authentication** (django-two-factor-auth).

1. Go to http://127.0.0.1:8000 — you will be redirected to the login page.
2. Enter your username and password.
3. The app will email you a one-time code. In local dev, the code is **printed in the terminal** where the server is running (no real email is sent).
4. Enter the code to complete login.

**Default dev credentials** (created during initial setup or reset manually):

| Field | Value |
|---|---|
| Username | `admin` |
| Password | `admin1234` (reset to whatever you set during `createsuperuser`) |

To reset a password at any time:

```bash
python manage.py changepassword admin
```

---

## Updating Dashboard Data (Workbook Uploads)

### Via Django Admin (normal workflow)

1. Log in and go to **http://127.0.0.1:8000/admin/**
2. Click **Workbook imports** in the sidebar
3. Click **Upload workbook** (top right of the list)
4. Select the dashboard category and upload the `.xlsx` file
5. The importer runs immediately and the dashboard shows the new figures on the next page load

### Supported workbook formats

| Category | Expected sheet structure |
|---|---|
| BWA | Sheets named by 4-digit year (e.g. `2023`, `2024`) |
| Mobile Network | Sheets named by 4-digit year; operator columns for MTN, Telecel, AT |
| Mobile Network (Regulatory Fees) | Sheets named by 4-digit year with quarterly fee rows |
| BWA Quarterly | Sheet named `20. BWA Subs per Operator` with quarter columns |

The importer validates:
- File extension (`.xlsx`, `.xlsm`, `.xls` only)
- Magic bytes (ZIP header for `.xlsx`/`.xlsm`; OLE2 for `.xls`) — rejects disguised files
- File size (20 MB limit)
- Sheet naming
- Metric label matching (uses aliases defined in `MetricDefinition`)

### Re-seeding from scratch

If the database is wiped or you start fresh:

```bash
python manage.py seed_reference_data   # must run first
python manage.py seed_dashboard_data   # loads the original HTML embedded figures
```

---

## Dashboard Pages

### Index page — `/`

Lists all active dashboard categories as cards. Clicking a card goes to the detail page.

### Detail page — `/dashboards/<slug>/`

Each dashboard renders:

- **Header** — category name, icon, description, year selector, live data badge
- **KPI cards** — Revenue, EBITDA, Net Profit, Total Assets, Debt, Enterprise Value (or Regulatory Payment for ICH)
- **Executive Intelligence** — auto-generated narrative with mini-stat cards
- **Charts (Chart.js)**:
  - Revenue, EBITDA, Net Profit (line for all-years, bar for single year)
  - Profitability Margins
  - Expenditure, Cost of Sales, CAPEX
  - Assets, Liabilities, Equity, Debt
  - Enterprise Value
  - 1% Regulatory Payments (ICH only — appears automatically if fee data exists)
- **Complete Financial Data table** — filterable by year, exportable as CSV
- **Notes** — saved per-dashboard in browser localStorage

### API endpoints (authenticated)

| Endpoint | Description |
|---|---|
| `GET /dashboards/<slug>/api/metrics/?year=all` | All financial values for a category |
| `GET /dashboards/<slug>/api/fees/` | Regulatory fee values (invoice, payment, outstanding) |

Both require a valid logged-in session. They return JSON.

---

## Key Design Decisions

### Data model
All financial figures are stored in a single normalised `FinancialValue` table keyed by `(category, company, period, metric)`. This means adding a new dashboard category requires only seeding new `MetricDefinition` rows — no schema changes.

### Metric keys
Django stores metric keys as hyphenated slugs (e.g. `cost-of-sales`, `ebitda-margin`). The dashboard JS maps these to camelCase (e.g. `costOfSales`, `ebitdaMargin`) using a `KEY_MAP` object in `detail.html`. If you add new metrics, add the mapping there too.

### Upload validation
`workbooks/validation.py` mirrors the validation pattern from the NCA Dodzi project. It checks magic bytes, not just file extension, so renamed non-Excel files are rejected before reaching openpyxl.

### Content Security Policy
`config/middleware.py` sets a CSP on every response. `'unsafe-inline'` is allowed for `script-src` because the dashboard JS uses Django template tags (`{% url %}`) to generate API URLs — these must be inline. If you move to a nonce-based approach in future, remove `'unsafe-inline'` and add a nonce to the script tag and CSP header.

### Two-factor auth
All views require `@login_required`. The `LOGIN_URL` is set to `two_factor:login` so unauthenticated requests redirect to the 2FA login page. In local dev, OTP codes appear in the terminal. In production, configure a real email backend via the `EMAIL_BACKEND` and related env variables.

---

## Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | Yes (prod) | Long random string. Dev falls back to `dev-only-change-me` when `DJANGO_DEBUG=True` |
| `DJANGO_DEBUG` | No | `True` for local dev. Defaults to `False` |
| `DJANGO_ALLOWED_HOSTS` | Yes | Comma-separated hostnames, e.g. `localhost,127.0.0.1` |
| `DATABASE_ENGINE` | No | Set to `sqlite` to use SQLite. Omit to use PostgreSQL |
| `POSTGRES_DB` | Prod | PostgreSQL database name |
| `POSTGRES_USER` | Prod | PostgreSQL user |
| `POSTGRES_PASSWORD` | Prod | PostgreSQL password |
| `POSTGRES_HOST` | Prod | PostgreSQL host (default `localhost`) |
| `POSTGRES_PORT` | Prod | PostgreSQL port (default `5432`) |
| `EMAIL_BACKEND` | No | Django email backend. Use `django.core.mail.backends.console.EmailBackend` locally |
| `DEFAULT_FROM_EMAIL` | No | From address for system emails |
| `OTP_EMAIL_SENDER` | No | From address for OTP emails |

---

## Switching to PostgreSQL (Production)

1. Remove `DATABASE_ENGINE=sqlite` from your `.env`
2. Add the `POSTGRES_*` variables with your database credentials
3. Run `python manage.py migrate`
4. Run `python manage.py seed_reference_data && python manage.py seed_dashboard_data`
5. Create a superuser: `python manage.py createsuperuser`

---

## Adding a New Dashboard Category

1. Add the category slug and name to `CATEGORIES` in `seed_reference_data.py`
2. Add the company slug and name to `COMPANIES` in `seed_reference_data.py`
3. Add the category slug to the loop that seeds `BWA_METRICS` (or define a custom metric list)
4. Run `python manage.py seed_reference_data`
5. If the new category has an Excel importer, add a handler in `workbooks/services/importer.py` — add a branch in `import_workbook()` matching the new category slug
6. Add the category icon to the `ICON_MAP` in `templates/dashboards/detail.html`
7. Upload a workbook through Django Admin to populate the data

---

## Outstanding / Not Yet Built

- **Mobile Network and Terrestrial Fibre dashboards** — metric definitions are seeded but no embedded data. A workbook upload is needed to populate them.
- **Workbook upload preview** — the importer currently commits immediately. A draft/preview/confirm flow was described in the original handoff but not yet implemented.
- **Per-user permissions** — all authenticated users currently see all dashboards. No per-dashboard view or upload permissions exist yet.
- **Export controls** — CSV export works on the frontend. Server-side bulk export (e.g. full database export to Excel) is not built.
- **Production deployment config** — no Dockerfile, no Gunicorn config, no Nginx config. The app runs on Django's dev server locally.
- **Static files in production** — run `python manage.py collectstatic` and configure a static file server or WhiteNoise if deploying.

---

## Troubleshooting

### Dashboard shows "Loading…" and never populates
The browser's Content Security Policy is probably blocking the inline JS. Check `config/middleware.py` — `script-src` must include `'unsafe-inline'`.

### "Error loading data" badge on the dashboard
The JS fetch to the API is failing. Check:
1. You are logged in (session cookie present)
2. The API endpoint returns JSON: open `/dashboards/<slug>/api/metrics/?year=all` directly in the browser tab
3. The database has data: run `python manage.py shell -c "from dashboards.models import FinancialValue; print(FinancialValue.objects.count())"`

### Template tags rendering as literal text
You are opening the HTML file directly in a browser (file:// URL) instead of going through the Django server. Always use `http://127.0.0.1:8000`.

### `ImproperlyConfigured: DJANGO_SECRET_KEY must be set`
Your `.env` file is missing or `DJANGO_DEBUG` is `False` without a proper secret key. Set `DJANGO_DEBUG=True` in `.env` for local dev.

### `IntegrityError: NOT NULL constraint failed: dashboards_workbookimport.uploaded_by_id`
This was fixed — the admin's `add_view` now redirects to the custom upload page, and `save_model` auto-sets `uploaded_by`. If you see it, make sure you're using the **Upload workbook** link, not the standard Django Admin **Add** button.

### Two-factor OTP code not arriving
In local dev the code is printed in the terminal. In production you need a working email backend. Set `EMAIL_BACKEND`, `DEFAULT_FROM_EMAIL`, and `OTP_EMAIL_SENDER` in your `.env`.
