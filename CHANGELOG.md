# CHANGELOG.md — LeadFlow CRM

All notable changes to this project, dated.

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