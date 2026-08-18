# PROGRESS.md — LeadFlow CRM

> Single source of truth for "where we are / where we stopped / what's next / blockers".
> Updated at the end of every working session. **Any agent: read this file first.**

## Current state
**Phase 9 (acquisition fields + saved Reports/Dashboards) done and verified.** Phases 0, 1, 2, 3, 5, 6, 7, 8 done; Phase 4 coded + mocked-verified (needs real Google Cloud OAuth creds).

## What is done
- Phase 0 fully: repo cloned, git identity set, MAPTOOL3 heritage copied to `app/map/heritage/`, docs written, scaffold pushed.
- Phase 1 fully: Flask app skeleton (factory + 6 blueprints), DB schema + settings seed, importer (dealer layout, contact-cell regex parser, latin-1/UTF-8 autodetect, **idempotent** Investor grouping), matching engine (hard/probable/soft), import UI with preview, match review, lead list + detail + outcome logging. Visual identity theme.css + base templates.
- Phase 2 fully: dedicated **Today queue** (`/today`): callbacks due + fresh queue (hard matches AND replied leads excluded), region->oldest. Outcome logging flips lead status. Verified.
- **Rich SharePoint export layout supported** (importer): 38-column tab-separated files import cleanly; `Blocked by signed dealer?` = `Block` sets lead status `blocked` (excluded from Today). Verified.
- **Phase 3 (Map) verified live**: dots-only + geocoding (Nominatim, PLZ fallback) + isochrones (ORS v2, 20/30-min, DB cache). Fixed stale-cache bug. ORS key stored locally.
- **Phase 5 (Reporting) complete**: Today summary badges; activity by day + by region; pipeline counts; callbacks due; EOD export (`;` + BOM, German Excel/SharePoint); leads CSV export honoring filters. Verified.
- **Phase 4 (Gmail) coded + mocked-verified**: OAuth flow (gmail.readonly, token at `data/gmail_token.json`), reply poller matching sender email/domain to contacts -> `email/replied` activity, dedupe via `activities.gmail_msg_id` (migration added), "Replied" badge on leads/Today, replied leads excluded from Today queue, Connect/Poll/Disconnect in Settings. Verified with mocked API; **needs real Google Cloud OAuth client to test live.**
- **Phase 6 (data load) done**: all real CSVs imported (see below). `responsible` field added to `leads` (from the `Responsible` column in OriginalG.csv), shown on leads list, lead detail, and leads CSV export.
- **Phase 8 (auth, user profiles, HTTPS) done and verified**:
  - Login required app-wide (Flask-Login); `/login`, `/logout`; CSRF on every POST (Flask-WTF, no time limit); session cookie HttpOnly + SameSite=Lax (+ Secure behind proxy).
  - **Maptool-V3-style login lockout**: sliding-window rate limiter (~15 attempts/min cadence) + persisted per-user lock (15 min) after overflow; admin can unlock in Users page. Configurable in Settings (`login_max_attempts`, `login_window_seconds`, `login_lock_seconds`).
  - Roles: **admin + user**. Admin-only: Users page (create/disable/unlock/reset pw), Settings (incl. Gmail + wipe), Import/Matches. Normal users see **only their own leads** (visibility = `leads.responsible` equals their display name) on Leads, Today, Dashboard, Reports, Map, and exports; direct access to a foreign lead returns 404.
  - Profile page (change display name/password); sidebar shows user + Sign out; `flask create-user` CLI bootstrap.
  - `users` table added (schema in `app/db.py`; migration not needed, table is new). SECRET_KEY auto-generated to `data/secret_key` (or env `LEADFLOW_SECRET`), never hardcoded.
  - **HTTPS**: `serve.py` (Waitress, 127.0.0.1:5000) + `Caddyfile` (Caddy reverse proxy, `tls internal`, https://localhost:4443) + `start-secure.bat`. ProxyFix (Werkzeug) so Flask builds correct https URLs (Gmail OAuth redirect URI). Plain HTTP rejected (400).
  - Fixed "pages show nothing": the app only bound 127.0.0.1:5000; behind Caddy it's reachable on the LAN at `https://<host>:4443`.
  - Verified live: anon -> redirect to login; admin + user logins; lockout after 16 failed attempts (correct pw blocked while locked, persisted); CSRF 400 on tokenless POST; all 12 routes 200 as admin; scoped views for user (116/1054 leads, foreign lead 404); HTTPS login + Secure cookie + dashboard; dev `run.py` still works on plain HTTP.
- **Phase 9 (acquisition fields + saved Reports/Dashboards) done and verified**:
  - **Acquisition fields persisted on `leads`** (per user decision, not on `companies`): `last_status`, `entrypoint`, `gad_status` (export `Status`, renamed to avoid clashing with `leads.status`), `sales_service`, `acquisition_status`, `acquisition_progress`. Added via `MIGRATIONS` (idempotent), so existing DBs upgrade in place.
  - **Step dates in a new `pipeline_events` table** (per user decision): `id, lead_id (FK leads, ON DELETE CASCADE), step_key, step_label, step_date (ISO), UNIQUE(lead_id, step_key)`. Canonical step list `PIPELINE_STEPS` (01..21 + LOI) in `app/importer.py`. `normalize_date` handles `M/D/Y`, `D.M.Y`, and ISO inputs.
  - **Importer** (`app/importer.py`): `scan_acquisition_columns` detects the rich-export columns by header (any of `Last Status`/`Entrypoint`/`Status`/`Sales & Service?`/`Acquisition Status`/`Acquisition Progress`/step-date headers like `01. First contact`); `import_lead_csv` now writes the 6 fields + 22 pipeline events. **Re-import of an existing lead now UPDATES it** (per user decision "changeable via upload") instead of skipping — stats now report `leads_updated`.
  - **Blocklist upload** (`app/views/imports.py`): if the uploaded blocklist file carries dealer columns (`investor`/`group`/`firma`/`company`/`firm`) OR acquisition columns, it is routed through `import_lead_csv` (lead source `blocklist`) so those rows **create/update leads too** (per user decision); the contacted rows for matching are still written as before.
  - **Lead edit UI**: POST `/leads/<id>/acquisition` updates the 6 fields + replaces the lead's pipeline events; lead detail page shows an **Acquisition** section with all 22 step-date inputs.
  - **Reporting engine** (`app/reporting.py`): source registry (`leads`, `activities`, `pipeline`) with dimensions/metrics/time fields; filters (eq / ne / contains); time presets (7d / 30d / 90d / this month / custom range); chart types **pie / bar / number**; `run_report` returns a `SimpleNamespace` (NOT a dict — a dict broke Jinja because `result.values` collides with the dict `.values()` method); visibility rule (`leads.responsible == user`) always applied for normal users.
  - **Saved Reports & Dashboards** (`app/views/reports.py`): `reports` table (`owner_id` FK users CASCADE, `name`, `kind` report|dashboard, `config_json`). Reports page shows a saved list + "New Report"/"New Dashboard". A **Dashboard is a collection of saved reports** (widgets on one page, Chart.js pie/bar/number cards). Saved reports/dashboards are **owner-only + admin sees all** (per user decision; a normal user gets 404 on someone else's report).
  - **Chart.js 4.4.4 vendored locally** at `app/static/vendor/chart.umd.min.js` (offline-safe, mirrors how Leaflet is included; no new Python deps).
  - Verified end-to-end on the real DB: rich export import (6 fields + 22 steps, ISO dates), re-import updates (1 lead updated, no dup), blocklist with dealer columns creates a lead + contacted row, acquisition edit UI saves all 22 steps, report preview/save/view/CSV-export all 200, dashboard + pie chart 200, saved list renders, owner scoping (user sees only own, 404 on admin's).
- **DATA NOTE (2026-08-18) — DB was found empty and was restored**: at the start of this session the main tables (`companies`, `leads`, `locations`, `contacts`, `matches`, `activities`, `opportunities`) were **already empty** while `contacted` (724), `users`, `settings` survived and `sqlite_sequence` still showed high watermarks (companies 1028, leads 1056) — i.e. rows were deleted, not a fresh DB. The emptied-table set exactly matches the cleanup loop in `data/test/verify_rich.py`. The wipe predates this session (first DB read returned nothing before any import ran). The wiped DB was backed up to `data/leadflow.db.wiped_backup`. The DB was rebuilt from the intact source CSVs (`C:\Users\Lenovo\Desktop\G\...`) using `data/bulk_import.py`; counts below match the documented Phase 6 state, then matching was re-run (943 matches). **Investigate verify_rich.py / any cleanup script before running it again.**

## Phase 6 import summary
- Imported (idempotent, source labels = clear file names):
  - `WOL.csv` -> source `WOL` (9 leads) — Wolfsburg research file.
  - `BWBA.csv` -> source `BWBA` (109 leads) — Ulm/Süd research file (uses `Investor (Dealer & Brands)` header; company keyword precedence fixed so `Investor` beats `Group`).
  - `Maike\Calw.csv` -> `Maike-Calw` (23), `Maike\Heilbronnfull.csv` + `Heilbronn.csv` -> `Maike-Heilbronn` (113), `Maike\Offenburg.csv` -> `Maike-Offenburg` (15), `Maike\Villingen-Schwenningenfull.csv` -> `Maike-VS` (18).
  - `Han\HAN.csv` + `HAN - Kopie.csv` -> `HAN` (94, Kopie deduped by idempotency).
  - `ORIGINALG.csv` -> `OriginalG` (673) — the "other" master file; contains the `Responsible` column (Lei/Willy/Erik/Jan/Thomas/Maike/Christian/Philipp) now stored in `leads.responsible`. **OriginalG.csv is itself a rich export** — during the Phase 9 restore it also populated `last_status`/`entrypoint`/`gad_status`/`sales_service`/`acquisition_status`/`acquisition_progress` and the `01. First contact` step date (672 leads).
- Totals (current, after Phase 9 restore + dedup): **1027 companies, 1054 leads, 1097 locations, 975 contacts**, 41 regions. Status: 875 `new`, 179 `blocked`. 0 duplicate leads (company+region+source).
  - Location count is **1097, not the Phase-6-documented 1103**: the Phase-6 count included 6 duplicate empty-address rows (`(company_id, address='', plz='')`); those were removed by a dedup pass (`DELETE` keeping MIN(id) per company+address+plz) during the Phase 9 cleanup. No real data lost.
- Encoding note: OriginalG.csv is latin-1 (umlauts decode correctly); other files are UTF-8 with BOM.

## Where we stopped
- Phase 9 done and verified (acquisition fields + saved Reports/Dashboards). Remaining: Phase 4 live Gmail test (needs Google Cloud creds), then any future/roadmap work.

## What is next (in order)
1. **Phase 4 live**: user creates Google Cloud OAuth client (Desktop app, scope gmail.readonly), pastes Client ID/Secret in Settings -> Connect -> Poll. Steps documented in README/blueprint §8. (Auth/HTTPS is in place; the callback redirect URI is now `https://<host>:4443/gmail/callback`.)
2. **HTTPS hardening when going to internet/VPS**: change Caddyfile from `https://localhost:4443` + `tls internal` to the real domain + `tls` (Let's Encrypt), open 443, keep Waitress on 127.0.0.1:5000.
3. Roadmap — deferred items (blueprint §15): isochrone-based blocking.

## Blockers
- Gmail live test needs Google Cloud OAuth client (user action).
- Small `responsible` inconsistency observed after restore (Erik 117 / Lei 248 vs the phase-8 count of Erik 116 / Lei 249): sum is identical (365) but one lead's owner differs. Probably a fix applied to the source data between sessions; not re-investigated. If per-owner counts matter, re-derive from OriginalG.csv rather than trusting either number.

## GitHub push status
- All local work is pushed to origin/main (Phases 0-9 + docs/blueprint updates). Release tag **`v0.7.0`** marks the Phase 9 state as a stable code fallback; README documents the fresh-machine restore steps. Data (DB) stays local and is backed up via `backup.bat`.

## Key decisions (for continuity)
- No separate `tasks` table: reminders are `activities` with `due_date` + status.
- Contact at Dealer is ONE cell -> regex extraction (email, phone, remainder = name).
- Data stays local; blocklist + lead CSV layout is the dealer layout in blueprint §5.
- Accent color `#C5B358` reserved for high-impact CTAs/underlines/badges only.
- Default country code for phone normalization = 49 (Germany), editable in Settings.
- Lead = one row in the dealer CSV; company = unique Investor (Group) name.
- `responsible` (owner) comes from the `Responsible` column of OriginalG.csv only; research files leave it empty.
- `OriginalG.csv` is the "other" master file (not the user's research); research files carry region-specific source labels.
- **Acquisition fields live on `leads`** (Phase 9): `last_status`, `entrypoint`, `gad_status`, `sales_service`, `acquisition_status`, `acquisition_progress`; step dates live in `pipeline_events` (22 canonical steps 01..21 + LOI). Rich-export and blocklist imports fill them; leads can be edited in the lead detail "Acquisition" section; re-imports UPDATE existing leads.
- **Auth**: roles are admin + user only. A normal user's visibility = leads where `leads.responsible` == their display name (admin sees all). Set the display name to the exact `Responsible` value when creating users.
- **Login lockout follows MAPTOOL3 cadence**: sequential attempts, ~15/min sliding window; on overflow the account is locked 15 min (persisted in `users.locked_until`). Settings keys `login_max_attempts`, `login_window_seconds`, `login_lock_seconds`.
- **Saved Reports/Dashboards are owner-only + admin sees all** (Phase 9). Dashboard = a collection of saved reports (widgets on one page). Chart.js is vendored locally (offline-safe).
- **Serving**: dev = `python run.py` (plain HTTP localhost). Secure = `start-secure.bat` -> Waitress on 127.0.0.1:5000 behind Caddy (TLS internal, https://localhost:4443). `LEADFLOW_COOKIE_SECURE=1` is set by start-secure.bat only. SECRET_KEY auto-generated to `data/secret_key` or `LEADFLOW_SECRET` env.

## Deferred (see blueprint §15) — do NOT miss
- Blocked leads via isochrones: build our OWN blocklist from the map — flag leads outside our driving-time operating range (ORS 20/30-min isochrones) as `blocked`; threshold setting in Settings; blocked status already excluded from Today.
- (Acquisition pipeline tracking — the old §15.1 — is **done** in Phase 9; remaining granularity like `LOI signed`/`Consors Quick Check Date` from the full 38-col export can be added later if the real file carries them.)

## Future ideas
- (none recorded yet)