# Implementation Blueprint — LeadFlow CRM (G_CRM_light)

> Live status: see `PROGRESS.md`. Phase checkboxes: see `PHASES.md`. Change history: see `CHANGELOG.md`.

## 0. Project summary
Self-hosted, single-user light CRM for cold outreach: CSV import (blocklist + sourced leads, dealer layout), relational CRM database, auto-dedup matching, daily call queue with built-in reminders, one-tap outcome logging, light reporting, Germany map (MAPTOOL3 heritage: geocoding + isochrones, dots-first, rate-safe). 100% local data. Visual identity per client spec.

## 1. Tech stack
- Python 3.11 + Flask + SQLite (stdlib `sqlite3`); server-rendered pages; no frontend build
- Deps: `flask`, `google-api-python-client`, `google-auth`, `google-auth-oauthlib`, `requests`, `python-dotenv`
- Map: Leaflet 1.9.4 (CDN) + OSM tiles; MAPTOOL3 logic ported to `/map`
- Geocoding: Nominatim (1.1s delay, `countrycodes=de`, PLZ fallback)
- Isochrones: OpenRouteService v2, strict rate discipline
- Startup: `start.bat` -> Flask -> `http://localhost:5000`

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
| `settings` | Country code, ORS key, Gmail path | -- |

No separate tasks table: callbacks/follow-ups are `activities` with `due_date` + `status`(open/done); the Today view is the task list.

## 5. CSV importers (dealer layout)
One row per lead. Headers (with intentional empty columns):
`Metro Area/State; City; [empty] [empty] [empty]; Investor (Group); Dealer Location Street; Dealer Location ZIP Code; [empty] [empty]; Contact at Dealer`

- **Contact at Dealer is ONE cell** (name + email + phone) -> parser extracts via regex (email pattern, phone pattern, remainder = name); preview shows extraction before import.
- Mapping: `Metro Area/State`->`companies.region`, `City`->`locations.city`, `Investor (Group)`->`companies.name`, street->`locations.address`, ZIP->`locations.plz`, contact->`contacts`.
- Same importer for the ~800 and ~250 files (same headers) - two import runs.
- Auto column-map + preview + confirm; saved mapping = one-click re-import; latin-1/UTF-8 auto-detect; idempotent; duplicate Investor (Group) rows auto-group into one company.

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
Calls/outcomes per day & region; pipeline counts; callback due list; dashboard cards. EOD export: one click -> today's outcomes as shared-Excel-friendly CSV for SharePoint paste. CSV export on any list.

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
See `PHASES.md` for the full checklist. Summary: 0 Repo/scaffold/docs, 1 Schema+importers+matching, 2 Today queue+reminders, 3 Map, 4 Gmail, 5 Reporting, 6 Data load, 7 Docs freeze.