# CHANGELOG.md — LeadFlow CRM

All notable changes to this project, dated.

## [0.6.1] — 2026-08-18
- **Backup & restore documented.** README gained a "Backup & restore" section: GitHub = code fallback (clone → pip install → `init-db` → `create-user` → run), data stays local (`backup.bat` → `LEADFLOW_backups\`). Release tag `v0.6.0` created at the Phase 8 commit as a stable restore point.

## [0.6.0] — 2026-08-18
- **Phase 8 (auth, user profiles, HTTPS) complete.**
- **Auth**: login required app-wide (Flask-Login) with `/login` + `/logout`; CSRF (Flask-WTF) on every POST; session cookie HttpOnly + SameSite=Lax (+ Secure behind the TLS proxy). No more open data wipe in Settings.
- **Login lockout (Maptool-V3 cadence)**: sliding-window rate limiter ~15 attempts/min per email+IP; on overflow the account locks 15 min (persisted in `users.locked_until`, survives restart) and even the correct password is rejected; admin unlock button in Users. Tunable via Settings `login_max_attempts` / `login_window_seconds` / `login_lock_seconds`.
- **Users & roles**: `users` table (email unique, display_name, password_hash, role, is_active, failed_attempts, locked_until, last_login). Admin-only Users page (create/disable/unlock/reset password), Settings, Import/Matches. `flask create-user --role admin` bootstrap CLI. Profile page (change display name/password).
- **Lead visibility**: normal users see only leads where `leads.responsible` == their display name, scoped across Leads, Today, Dashboard, Reports, Map, and CSV exports; direct access to a foreign lead returns 404. Admins see everything.
- **HTTPS**: `serve.py` (Waitress on 127.0.0.1:5000) behind `Caddyfile` reverse proxy (tls internal, https://localhost:4443) + `start-secure.bat`. ProxyFix so Flask builds https URLs (keeps Gmail OAuth redirect URI correct). Plain HTTP rejected. Fixes "pages show nothing on other devices" — app is now reachable on the LAN via the proxy instead of binding loopback-only.
- **Secrets**: SECRET_KEY auto-generated to `data/secret_key` (gitignored) or `LEADFLOW_SECRET` env; never hardcoded. New deps: `flask-login`, `flask-wtf`, `waitress`.
- Verified live: anon redirect; admin + user login; lockout after 16 attempts; CSRF 400 without token; all routes 200 as admin; user sees 116/1054 leads + foreign lead 404; HTTPS login with Secure cookie; dev `run.py` still works.
- Blueprint updated: new §16 (auth/user/HTTPS), deps, schema table, startup modes; PROGRESS push status updated. Pushed all commits to origin/main.

## [0.5.1] — 2026-08-18
- **Phase 7 (docs freeze) complete.** PROGRESS.md cleaned (removed duplicated stale sections), push status reflects data-load commit, deferred items listed under "Deferred (see blueprint §15)". PHASES.md marks Phases 6 and 7 done.

## [0.5.0] — 2026-08-18
- **Phase 6 (data load) complete — all real CSVs imported.**
- New `responsible` field on `leads` (schema + migration), populated from the `Responsible` column of `OriginalG.csv` (Lei/Willy/Erik/Jan/Thomas/Maike/Christian/Philipp). Shown on leads list, lead detail, and leads CSV export.
- Importer fix: company keyword precedence — `Investor (Dealer & Brands)` now wins over a separate `Group` column (affected BWBA research file).
- Imported (idempotent, clear source labels): WOL 9, BWBA 109, Maike-Calw 23, Maike-Heilbronn 113, Maike-Offenburg 15, Maike-VS 18, HAN 94, OriginalG 673. Duplicate files (`Heilbronn`/`Heilbronnfull`, `HAN - Kopie`) deduped by idempotency.
- Totals: 1027 companies, 1054 leads, 1103 locations, 975 contacts, 41 regions; 875 new + 179 blocked; 0 duplicate leads.
- Verified: fresh DB build from all source files; all pages 200; matcher scans all 1054 leads.

## [0.4.0] — 2026-08-18
- **Phase 4 (Gmail) complete — code + mocked e2e; needs a Google Cloud OAuth client for real testing.**
- Added `app/gmail_service.py`: OAuth flow (gmail.readonly, offline token to `data/gmail_token.json`), token refresh, reply poller (list inbox messages, match sender to contacts by exact email or domain, create `email/replied` activities, dedupe via `gmail_msg_id`).
- Added Gmail section to Settings: Client ID/Secret fields, Connect (OAuth redirect), Poll now, Disconnect; shows connected user.
- DB migration support (`MIGRATIONS` in `app/db.py`): added `activities.gmail_msg_id` column to existing DBs idempotently.
- "Replied" badge on leads list + Today; replied leads excluded from Today fresh queue (they responded already).
- Verified with mocked Gmail API: poll creates activity, dedupe holds, badge shows, all pages 200, migration applied.

## [0.3.4] — 2026-08-18
- **Phase 5 (Reporting) complete.**
- Reports page: added Today summary badges (calls, appointments, not-interested, callbacks, won).
- EOD export (`/reports/export/today`): now semicolon-delimited + UTF-8 BOM for German Excel / SharePoint paste.
- New leads CSV export (`/leads/export`) honoring current filters (region/status/match); export link on the leads list.
- Verified end-to-end: reports 200 with badges; EOD export BOM + `;` rows; leads export 6 rows, filtered export 1 row; leads page 200 with export link.

## [0.3.3] — 2026-08-18
- **Live-tested ORS isochrones** (`/map/isochrones`): new ORS API key works; fetched 20-min (1200s) + 30-min (1800s) isochrones for the München test location; `/map/locations` serves iso_json; second run skips cached (instant).
- Fixed bug: isochrone loop read stale in-memory `iso_json`, so the 20-min pass overwrote the 30-min cache. Now re-reads rows from DB per pass; both caches persist.
- (Note: first ORS key returned `403 Access to this API has been disallowed` on all services — account-level setting, resolved by user generating a new key.)

## [0.3.2] — 2026-08-18
- Blueprint §5a + §15: documented rich SharePoint export layout (38 cols) and deferred features — acquisition pipeline tracking (37 step-date columns) and **blocked leads via isochrones** (build our own blocklist from driving-time map range). Added matching PHASES.md section.
- **Live-tested geocoding** (`/map/geocode`, Nominatim): `Lindwurmstrasse 22-24, 80337 München` -> 48.1315, 11.5627 (`ok`); PLZ fallback `10115` -> 52.532, 13.384; markers endpoint returns geocoded points; `/map` renders 200. DB cleaned after test.

## [0.3.1] — 2026-08-18
- Importer: handle the **rich SharePoint export layout** (38 columns, tab-separated): maps `Metro Area/State`, `Investor (Group)`, `Dealer Location Street`, `Dealer Location ZIP Code`, `Contact at Dealer (Name, Mail, Phone)`.
- New `Blocked by signed dealer?` column: `Block` sets lead status to `blocked`, keeping it out of the Today call queue.
- Leads filter dropdown now includes `blocked`.
- Verified with a real export row (`Autohaus am Goetheplatz`, München): imported as source `test`, status `blocked`, all pages 200, excluded from Today.

## [0.3.0] — 2026-08-18
- Phase 2 complete: dedicated Today queue (`/today`).
- Added: Today view = callbacks due (activities with due_date <= today) + fresh queue (leads in new/called/no_answer/voicemail status, hard matches excluded), sorted region -> oldest.
- Added: sidebar Today nav entry.
- Improved: importer now idempotent — re-importing the same file creates no duplicate companies, locations, contacts, or leads (verified 3x import yields identical counts).

## [0.2.0] — 2026-08-18
- Phase 1 complete: data core verified end-to-end.
- Added: Flask app skeleton (factory + blueprints: main, leads, imports, map, reports, settings), `run.py`, `start.bat`.
- Added: relational SQLite schema (`companies`, `locations`, `contacts`, `leads`, `opportunities`, `activities`, `contacted`, `matches`, `settings`) with indexes + default settings seed.
- Added: dealer-layout CSV importer with contact-cell regex parser (name/email/phone), encoding autodetect (latin-1/UTF-8), Investor (Group) auto-grouping, column-mapping preview.
- Added: dedup matching engine (hard/probable/soft confidence rules), match review UI, re-run matching.
- Added: lead list/detail pages with one-tap outcome logging (callback -> due_date reminder, status transitions).
- Added: visual identity theme.css (bg #1A1A1B, text #F5F5F2, accent #C5B358) + base templates.
- Added: dots-only map view (Leaflet+OSM), Nominatim geocode action, rate-limited ORS isochrone fetch with DB cache.
- Added: light reporting (pipeline, by-day, by-region, callbacks due) + today-outcomes CSV export.
- Verified: import + matching + outcome flow against test CSVs (`data/test/`); all routes 200.

## [0.1.0] — 2026-08-18
- Phase 0: initialized repo scaffold.
- Added: project blueprint, phase/status/changelog docs, AGENTS handoff conventions.
- Added: MAPTOOL3 heritage copied into `app/map/heritage/` (index, geocode.py, dedupe.py, plz geojson, plans).
- Added: Python/Flask dependency list, `start.bat`, `backup.bat`, `.gitignore`.
- Added: Flask app skeleton + SQLite schema module (in progress at time of writing).