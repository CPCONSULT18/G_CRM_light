# Implementation Blueprint — LeadFlow CRM (G_CRM_light)

> Live status: see `PROGRESS.md`. Phase checkboxes: see `PHASES.md`. Change history: see `CHANGELOG.md`.

## 0. Project summary
Self-hosted, single-user light CRM for cold outreach: CSV import (blocklist + sourced leads, dealer layout), relational CRM database, auto-dedup matching, daily call queue with built-in reminders, one-tap outcome logging, light reporting, Germany map (MAPTOOL3 heritage: geocoding + isochrones, dots-first, rate-safe). 100% local data. Visual identity per client spec.

## 1. Tech stack
- Python 3.11 + Flask + SQLite (stdlib `sqlite3`); server-rendered pages; no frontend build
- Deps: `flask`, `flask-login`, `flask-wtf`, `waitress`, `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `requests`, `python-dotenv`
- Map: Leaflet 1.9.4 (CDN) + OSM tiles; MAPTOOL3 logic ported to `/map`
- Geocoding: Nominatim (1.1s delay, `countrycodes=de`, PLZ fallback)
- Isochrones: OpenRouteService v2, strict rate discipline
- Startup (dev): `start.bat` -> Flask -> `http://localhost:5000`
- Startup (secure/LAN): `start-secure.bat` -> Waitress (`serve.py`, 127.0.0.1:5000) behind Caddy reverse proxy -> `https://localhost:4443` (`Caddyfile`, `tls internal`; real domain + Let's Encrypt when public)

## 2. Repository
- Private-then-public repo `github.com/CPCONSULT18/G_CRM_light` (now public).
- MAPTOOL3 files copied into repo as `app/map/heritage/`; Desktop originals untouched.
- Files: this blueprint, `CHANGELOG.md`, `PHASES.md`, `PROGRESS.md`, `README.md`, `AGENTS.md`, app code.

## 3. Progress / troubleshooting handoff
- `PROGRESS.md` = where we are / stopped / next / blockers, updated every session.
- `PHASES.md` = phase checkboxes + acceptance criteria.
- `CHANGELOG.md` = dated entries per change.
- Any agent resumes from `PROGRESS.md` first.

## 4. Database schema (real CRM)
| Table | Purpose | Relations |
|---|---|---|
| `companies` | Investor (Group) = the client | 1-N locations, 1-N contacts, 1-N leads |
| `locations` | Dealer locations (street, city, plz, lat, lng, iso_cache) | N-1 companies |
| `contacts` | Contact at dealer (name, email, phone) | N-1 companies |
| `leads` | Sourced leads, source/region/qual_score/status | N-1 companies |
| `opportunities` | Pipeline: Interested -> Appointment -> Won/Lost | N-1 leads |
| `activities` | Calls/emails/inbound + outcomes + due_date (reminder engine) | N-1 leads |
| `contacted` | Imported blocklist | -- |
| `matches` | Dedup (lead<->contacted, field, confidence) | N-1 leads, N-1 contacted |
| `settings` | Country code, ORS key, Gmail path, login lockout tuning | -- |
| `users` | App logins: email, display_name, password_hash, role (admin/user), is_active, failed_attempts, locked_until, last_login | -- |

No separate tasks table: callbacks/follow-ups are `activities` with `due_date` + `status`(open/done); the Today view is the task list.

**Visibility rule:** a normal user sees only leads where `leads.responsible` == their `display_name`; admins see everything. Roles are admin + user only.

## 5. CSV importers (dealer layout)
One row per lead. Headers (with intentional empty columns):
`Metro Area/State; City; [empty] [empty] [empty]; Investor (Group); Dealer Location Street; Dealer Location ZIP Code; [empty] [empty]; Contact at Dealer`

- **Contact at Dealer is ONE cell** (name + email + phone) -> parser extracts via regex (email pattern, phone pattern, remainder = name); preview shows extraction before import.
- Mapping: `Metro Area/State`->`companies.region`, `City`->`locations.city`, `Investor (Group)`->`companies.name`, street->`locations.address`, ZIP->`locations.plz`, contact->`contacts`.
- Same importer for the ~800 and ~250 files (same headers) - two import runs.
- Auto column-map + preview + confirm; saved mapping = one-click re-import; latin-1/UTF-8 auto-detect; idempotent; duplicate Investor (Group) rows auto-group into one company.

### 5a. Rich SharePoint export layout (supported import format)
Real exports are the **38-column tab-separated** sheet, not just the 11-column dealer layout. Headers include:
`Responsible; Metro Area/State; City; City Rank; Top City Population; Investor (Group); Dealer Location Street; Dealer Location ZIP Code; Blocked by signed dealer?; Contact at Dealer (Name, Mail, Phone); Last Status; Entrypoint; Status; Sales & Service?; Acquisition Status; Acquisition Progress; [01..21 acquisition step dates]`

Imported (verified with real rows): region, city, company, street, ZIP, contact cell, `Blocked by signed dealer?` (value `Block` -> lead status `blocked`, excluded from Today), `Responsible` -> `leads.responsible`, and — since Phase 9 — the **acquisition data**: `Last Status`/`Entrypoint`/`Status`/`Sales & Service?`/`Acquisition Status`/`Acquisition Progress` stored on `leads` (`gad_status` is used for export `Status` to avoid clashing with `leads.status`), and the `01. First contact` … `21. Signed contract distributed` step dates stored in `pipeline_events`. See §15.1.

## 6. Matching engine
Normalize (email lower; phone->E.164 +country; domain->base; name->strip legal forms) vs `contacted`:
- **Hard:** email 1:1 exact; phone + name both
- **Probable:** phone alone; domain + fuzzy name
- **Soft:** domain alone; name alone
Badge on leads, review page, re-runnable.

## 7. Today queue + reminders
Leads excluding hard matches, sorted region -> oldest. One-tap outcomes: Called / Not interested / Callback(+date) / No answer / Voicemail / Appointment booked -> logged to `activities`, drives pipeline. Callback creates activity with `due_date` -> auto-reappears that day.

## 8. Gmail integration (Phase 4, deferred)
OAuth `gmail.readonly`, token local, poller -> inbound activity + "Replied" badge.

## 9. Map (dots-first, rate-safe)
`/map` starts dots-only (no key). Settings field to paste ORS key -> enables 20/30-min isochrones. Rate discipline ported from MAPTOOL3: free tier ~500 req/day; two-phase fetch (30-min then 20-min); batches of 5 with 15s pause; per-location DB cache; skip stale; honor 429 `Retry-After`; status line shows quota/pending before runs. Geocode action on empty lat/lng with PLZ fallback.

## 10. Reporting
Calls/outcomes per day & region; pipeline counts; callback due list; dashboard cards. EOD export: one click -> today's outcomes as shared-Excel-friendly CSV for SharePoint paste. CSV export on any list. **Saved Reports & Dashboards (Phase 9)**: a report = source (`leads`/`activities`/`pipeline`) + dimension + metric + optional data/time filters + chart type (pie/bar/number), with live preview; a dashboard = a collection of saved reports rendered as Chart.js widgets on one page; saved items are owner-only + admin-sees-all; CSV export of a saved report. Chart.js is vendored locally (offline-safe). Engine in `app/reporting.py`; `run_report` returns a `SimpleNamespace` (a dict breaks Jinja because `result.values` collides with dict's `.values()`).

## 11. Visual identity (strict)
- Primary bg: `#1A1A1B` (deep charcoal)
- Secondary/text: `#F5F5F2` (bone/off-white)
- Accent: `#C5B358` (muted champagne gold) - ONLY for high-impact CTAs, underlines, critical badges
- 1px hairline borders only; generous whitespace; "carved" text feel
- Single `theme.css` applied globally

## 12. Data migration
Import ~800 + ~250 CSVs, run dedup, verify counts, snapshot before/after.

## 13. Backup
`backup.bat` -> timestamped copy of `data/leadflow.db`.

## 14. Phases
See `PHASES.md` for the full checklist. Summary: 0 Repo/scaffold/docs, 1 Schema+importers+matching, 2 Today queue+reminders, 3 Map, 4 Gmail, 5 Reporting, 6 Data load, 7 Docs freeze, 8 Auth + user profiles + HTTPS, 9 Acquisition fields + saved Reports/Dashboards.

## 16. Auth, user profiles, HTTPS (Phase 8)
- **Login**: Flask-Login app-wide; `/login` + `/logout`; CSRF (Flask-WTF) on every POST; session cookie HttpOnly + SameSite=Lax, Secure when behind the TLS proxy (`LEADFLOW_COOKIE_SECURE=1`, set by `start-secure.bat`). Unauthenticated requests redirect to `/login?next=...` (open-redirect guarded).
- **Lockout (Maptool-V3 cadence)**: sliding-window rate limiter keyed email+IP, default ~15 attempts/min (`login_max_attempts`/`login_window_seconds` in Settings). On overflow the user row is locked `login_lock_seconds` (default 900) via `users.locked_until` (persisted, survives restart); even a correct password is rejected while locked. Admin unlocks in the Users page.
- **Roles**: `admin` (Users page incl. create/disable/unlock/reset pw; Settings incl. Gmail + wipe; Import/Matches) and `user` (own leads only via the responsible==display_name visibility rule above). Bootstrap: `flask create-user --email ... --role admin`. Profile page changes display name/password.
- **HTTPS**: production runs Waitress on 127.0.0.1:5000 behind Caddy (`tls internal` on LAN; swap to a real domain + `tls` for Let's Encrypt when public). ProxyFix (Werkzeug) so Flask sees `X-Forwarded-Proto` and builds correct https URLs — this keeps the Gmail OAuth redirect URI (`https://<host>:4443/gmail/callback`) valid. Plain HTTP on the proxy port is rejected.
- **Secrets**: `SECRET_KEY` auto-generated to `data/secret_key` (gitignored) or via `LEADFLOW_SECRET` env; never hardcoded. Gmail token + ORS key stay in `data/` (gitignored).

## 15. Deferred features (do NOT miss - revisit after core phases)
These were intentionally scoped out to avoid feature creep, but are explicit future work. Track here, not in code.

### 15.1 Acquisition pipeline tracking
The rich export carries the full GAD dealer-acquisition pipeline as **37 date columns** (steps `01. First contact` ... `21. Signed contract distributed`, plus `LOI signed`, `Consors Quick Check Date`, etc.) plus `Last Status`, `Entrypoint`, `Status`, `Sales & Service?`, `Acquisition Status`, `Acquisition Progress`.

**DONE in Phase 9** (user-requested feature):
- The 6 summary fields (`Last Status`, `Entrypoint`, `Status`, `Sales & Service?`, `Acquisition Status`, `Acquisition Progress`) are stored **on `leads`** (`gad_status` = export `Status`, to avoid clashing with `leads.status`). Added via `MIGRATIONS`, idempotent on existing DBs.
- The step dates are stored in a **`pipeline_events`** table: `id, lead_id (FK leads ON DELETE CASCADE), step_key, step_label, step_date (ISO), UNIQUE(lead_id, step_key)`. Canonical `PIPELINE_STEPS` = `01`..`21` + `LOI`. `normalize_date` handles M/D/Y, D.M.Y, ISO.
- Importer scans for acquisition columns by header; re-importing an existing lead **updates** it (idempotent) instead of skipping; blocklist uploads carrying dealer/acquisition columns also create/update leads.
- UI: lead detail shows an **Acquisition** section with all 22 step-date inputs (POST `/leads/<id>/acquisition`).
- Reporting: acquisition fields + pipeline steps are dimensions in the reporting engine.
- Residual: if the real export carries extra step columns (`LOI signed`, `Consors Quick Check Date` …), extend `PIPELINE_STEPS`/`scan_acquisition_columns` to keep them (dedupe on re-import already holds). Test file: `data/test/test_rich_export.tsv` (gitignored).

### 15.2 Blocked leads via isochrones (build our own blocklist from the map)
The `Blocked by signed dealer?` column only covers dealers already signed by the company. The real "do not call" list should be **ours, derived from the map**: mark leads blocked/unreachable based on **driving-time isochrones** (e.g. > X minutes from us on the ORS 20/30-min maps).
- Idea: from the `/map` view, select isochrones that represent our operating range; leads whose locations fall outside (or beyond a chosen threshold) get flagged `blocked` automatically - our own version of the blocklist, self-maintained, not dependent on the export column.
- Later goal: a "block by isochrone" action on the map + a threshold setting in Settings; blocked leads excluded from Today (already wired: status `blocked` is filtered out).
- Not yet implemented. This is why the importer sets `blocked` from the export column today - same status feeds the same exclusion.