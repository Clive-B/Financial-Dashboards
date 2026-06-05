# Security Audit: Current Financial Dashboard Repo

Date: 2026-06-05

## Executive Summary

The current repository is not yet a server application. It is a collection of static HTML dashboards that parse uploaded Excel files in the browser, store results in `localStorage`, and load JavaScript/CSS dependencies from public CDNs. There is no authentication, authorization, central database, server-side validation, audit trail, or two-factor authentication because there is no backend yet.

The most important security move is the planned Django/Postgres migration: put uploads behind Django Admin, require 2FA for staff, validate workbooks server-side, store canonical financial data in Postgres, and serve dashboards from authenticated views/APIs.

## Findings

### F-001: No Authentication Or Authorization Boundary

- Rule ID: APP-AUTH-001
- Severity: High
- Location: All dashboard HTML files, for example `Mobile Network Financial Dashboard.html:110-204` and `BWA Financial Dashboard.html:77-189`
- Evidence: The dashboards are static pages with upload buttons and JavaScript handlers, but no server-side login, permission checks, sessions, or roles.
- Impact: Anyone with the file can open it, upload data locally, export data, and view embedded financial figures. There is no distinction between admin uploaders and dashboard viewers.
- Fix: Move dashboard serving into Django authenticated views. Keep uploads in Django Admin and enforce per-dashboard permissions.
- Mitigation: Until Django exists, treat these HTML files as internal-only artifacts and do not host them publicly.
- False positive notes: Authentication could exist outside this repo only if a separate portal wraps these files. That is not visible here.

### F-002: Uploaded Financial Data Is Stored In Browser localStorage

- Rule ID: JS-STORAGE-001
- Severity: Medium
- Location: `Mobile Network Financial Dashboard.html:874`, `Mobile Network Financial Dashboard.html:1052`, `Mobile Network Financial Dashboard.html:1631`, `BWA Financial Dashboard.html:581`, `ICH Financial Dashboard.html:675`, `Pay Television Financial Dashboard.html:595`, `Terrestrial Fibre Financial Dashboard.html:581`, `Tower Infrastructure Financial Dashboard.html:581`
- Evidence: Browser storage calls save parsed workbook snapshots with `localStorage.setItem(...)`.
- Impact: Financial data can persist on shared machines, survive browser restarts, and be read by any script that runs on the same origin. It also creates inconsistent data between users.
- Fix: Store uploaded data centrally in Postgres. Use `localStorage` only for harmless UI preferences, not financial datasets or notes.
- Mitigation: Add clear handling instructions for local static files and ask users to clear browser storage after testing.
- False positive notes: The current files do not store passwords or tokens in localStorage. The issue is persistence and confidentiality of financial data.

### F-003: Dynamic HTML Rendering Uses innerHTML Heavily

- Rule ID: JS-XSS-001
- Severity: Medium now, High if untrusted workbook text reaches these sinks
- Location: Examples include `Mobile Network Financial Dashboard.html:612`, `Mobile Network Financial Dashboard.html:1151`, `Mobile Network Financial Dashboard.html:1241`, `Mobile Network Financial Dashboard.html:1585`, `BWA Financial Dashboard.html:380`, `BWA Financial Dashboard.html:419`, `BWA Financial Dashboard.html:495`
- Evidence: Dashboard output is assembled with template strings and assigned to `innerHTML`.
- Impact: If attacker-controlled workbook content or future API data reaches these strings without escaping, it can become DOM XSS.
- Fix: During migration, render text with Django templates or DOM-safe APIs. For client rendering, build nodes with `textContent` or sanitize reviewed rich HTML before insertion.
- Mitigation: Use strict input validation and a Content Security Policy when the app is served by Django.
- False positive notes: Many current values appear numeric or constant. The risk increases as soon as company names, notes, labels, or workbook cells are treated as display text.

### F-004: Third-Party CDN Assets Are Loaded Without Integrity Controls

- Rule ID: JS-SUPPLYCHAIN-001
- Severity: Medium
- Location: `Mobile Network Financial Dashboard.html:8-14`, `BWA Financial Dashboard.html:7-9`, `ICH Financial Dashboard.html:7-9`, `Pay Television Financial Dashboard.html:7-9`, `Terrestrial Fibre Financial Dashboard.html:7-9`, `Tower Infrastructure Financial Dashboard.html:7-9`
- Evidence: External scripts and styles are loaded from jsdelivr, SheetJS CDN, cdnjs, and Font Awesome without Subresource Integrity.
- Impact: A compromised CDN path or dependency response can execute script with full page privileges.
- Fix: Vendor pinned assets into Django static files or add SRI hashes and a restrictive CSP.
- Mitigation: Prefer self-hosted static assets during the Django migration.
- False positive notes: CDN use is common for prototypes; production should not rely on unaudited third-party script execution.

### F-005: Workbook Parsing Happens Client-Side Without Server Validation Or Audit

- Rule ID: UPLOAD-VALIDATION-001
- Severity: High for the intended production workflow
- Location: `Mobile Network Financial Dashboard.html:617-744`, `Mobile Network Financial Dashboard.html:764-865`, `BWA Financial Dashboard.html:543-576`, `ICH Financial Dashboard.html:598-670`
- Evidence: FileReader and SheetJS parse uploads in the browser with no server-side validation, persistence controls, or import audit record.
- Impact: There is no trusted record of who uploaded what, when it changed, which cells changed, or whether malformed workbooks were rejected consistently.
- Fix: Move workbook upload and parsing to Django Admin. Validate file type, size, sheet names, metric aliases, numeric ranges, and import completeness. Store import logs and changed values in Postgres.
- Mitigation: Keep current upload path limited to local/internal use until the server workflow exists.
- False positive notes: Client-side parsing is acceptable for a private prototype, but it is not sufficient for a controlled financial data system.

### F-006: No Django Security Baseline Exists Yet

- Rule ID: DJANGO-BASELINE-001
- Severity: High before production launch
- Location: Repository root
- Evidence: No `manage.py`, `settings.py`, middleware configuration, CSRF setup, admin configuration, or deployment settings exist.
- Impact: The requested Postgres/Admin/2FA system still needs secure defaults from the beginning. Retrofitting these later is riskier.
- Fix: Scaffold Django with environment-based settings, strict `ALLOWED_HOSTS`, `DEBUG=False` in production, CSRF/session protections, secure cookie settings for TLS deployments, and `manage.py check --deploy` in CI.
- Mitigation: Do not deploy the dashboards as public static pages while the backend is being built.
- False positive notes: This is a design gap, not a code flaw in an existing Django app.

## Secure Target Controls

- Require login for all dashboard views and JSON endpoints.
- Require 2FA for all staff/admin users. Email OTP is acceptable as a starting point; TOTP or WebAuthn is stronger.
- Keep workbook uploads inside Django Admin initially.
- Validate uploads server-side before saving financial values.
- Use transactions for imports so partial data does not publish.
- Record upload actor, timestamp, checksum, parser version, status, errors, and changed values.
- Use Postgres `DecimalField` values for money and ratios.
- Move static JS/CSS into Django static files or pin CDN assets with SRI.
- Add CSP, nosniff, Referrer-Policy, frame protections, and CSRF protections.
- Add rate limiting for login and upload endpoints.
- Run dependency scanning once Python dependencies are introduced.

## First Fix Recommendation

Do not start by patching all static HTML XSS sinks. Start by creating the Django/Postgres foundation and moving upload authority into Django Admin. That removes the largest control gaps and gives us a safer place to migrate the current Chart.js UI incrementally.
