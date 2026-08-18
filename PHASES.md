# PHASES.md — LeadFlow CRM

Legend: `[ ]` pending · `[x]` done · `[~]` in progress · `[!]` blocked

## Phase 0 — Repo, scaffold, docs
- [x] Create/clone GitHub repo (CPCONSULT18/G_CRM_light)
- [x] Git identity configured (CPCONSULT18 / noreply email)
- [x] Copy MAPTOOL3 heritage into `app/map/heritage/`
- [x] Write `implementation_blueprint.md`
- [x] Write `CHANGELOG.md`, `PHASES.md`, `PROGRESS.md`, `README.md`, `AGENTS.md`
- [x] `requirements.txt`, `start.bat`, `backup.bat`, `.gitignore`
- [x] Initial push of scaffold
- **Acceptance:** repo reachable, scaffold commits pushed, docs accurate.

## Phase 1 — Data core: schema, importers, matching
- [x] Flask app skeleton (factory, blueprints, db init)
- [x] DB schema module (`app/db.py`) + `settings` seed
- [x] `theme.css` (visual identity) + `base.html`
- [x] Importer: dealer layout + contact-cell parser + encoding autodetect + grouping
- [x] Matching engine (normalize + hard/probable/soft)
- [x] Import UI (upload/preview/map/confirm) + dedup review UI
- [x] Lead list + detail pages
- [x] Test with sample CSVs, run app, verify DB
- **Acceptance:** import sample ~800-like file; contact cell parses; groups by Investor; dedup flags matches; pages render. ✅ Verified end-to-end with test data.

## Phase 2 — Call day
- [ ] Dedicated `/today` view: leads minus hard matches, region -> oldest
- [~] One-tap outcome logging + callback due_date reminders (works on lead detail page; port to Today)
- [ ] Pipeline status transitions (partially done via outcome map)
- **Acceptance:** call a test lead, log outcome, callback reappears on date.

## Phase 3 — Map
- [ ] `/map` dots-only view (Leaflet + OSM)
- [ ] Geocode action (Nominatim, PLZ fallback)
- [ ] ORS isochrones (rate-safe, DB cache, quota status line)
- **Acceptance:** upload sample, geocode empties, trigger rate-limited isochrone run.

## Phase 4 — Gmail (deferred)
- [ ] OAuth client flow (gmail.readonly)
- [ ] Poller -> inbound activity + Replied badge
- **Acceptance:** reply to test email surfaces on lead.

## Phase 5 — Reporting
- [ ] Daily/region outcome reports + pipeline counts + callback due list
- [ ] EOD export to shared-Excel layout
- **Acceptance:** report numbers match logged activities.

## Phase 6 — Data load
- [ ] Import ~800 + ~250 real CSVs, run dedup, verify counts, snapshot
- **Acceptance:** counts match source, no data loss.

## Phase 7 — Docs freeze
- [ ] Final changelog, PROGRESS handoff, README polish
- **Acceptance:** `PROGRESS.md` fully describes state for next agent.