# CHANGELOG.md — LeadFlow CRM

All notable changes to this project, dated.

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