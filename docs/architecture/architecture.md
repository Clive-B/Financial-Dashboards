# Architecture Notes

## System Boundary

The new system is an internal financial dashboard platform. It owns workbook ingestion, financial metric normalization, dashboard API responses, dashboard rendering, admin permissions, and audit records.

Out of scope for the first build:

- Public anonymous dashboard access.
- Complex workflow approvals.
- Real-time collaboration.
- Data warehouse integration.
- Advanced forecasting beyond the current simple trend logic.

## Runtime Components

- Django web app: authentication, admin, dashboard templates, APIs.
- Postgres: canonical financial data, import records, user/session/admin metadata.
- Static assets: Chart.js dashboard JavaScript, CSS, icons, and downloaded chart helpers.
- Workbook storage: private media storage for original uploaded files.
- Email service: password reset and email 2FA delivery.

## Key Decisions

### Use Django Admin For Uploads First

Django Admin gives us authentication, permissions, CSRF, forms, validation hooks, and audit-friendly workflows quickly. A custom upload UI can come later if non-admin users need a polished ingestion experience.

### Use Postgres As Source Of Truth

Browser `localStorage` and embedded JavaScript constants are not a shared or auditable data store. Postgres gives us transactions, constraints, queryability, backups, and versioned import history.

### Keep Chart.js Initially

The existing dashboard UX already uses Chart.js. Keeping it reduces migration risk while the backend, data model, and security controls are built.

## Data Ownership

- Admin users own workbook uploads and import confirmations.
- The import service owns parsing and normalization.
- Postgres owns canonical values and audit history.
- Dashboard APIs own read-only presentation payloads.
- Client JavaScript owns chart rendering and UI state only.

## Risks

- Workbook layouts may vary across dashboard categories. Mitigation: parser fixture tests per category.
- Current JavaScript uses floats. Mitigation: use Python `Decimal` and explicit ratio normalization.
- Email 2FA depends on deliverability. Mitigation: support backup codes and plan for TOTP.
- Inline static HTML has many dynamic rendering paths. Mitigation: move data handling server-side before broad frontend cleanup.
- Public CDN scripts increase supply-chain risk. Mitigation: vendor static assets in Django.

## Build Order

1. Scaffold Django/Postgres with secure settings.
2. Add models and admin.
3. Port BWA importer first.
4. Add API and template for BWA.
5. Repeat importer/API/template migration for the remaining dashboards.
6. Add 2FA and production hardening before any external deployment.
