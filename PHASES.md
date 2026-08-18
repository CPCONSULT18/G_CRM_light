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
- [x] Dedicated `/today` view: leads minus hard matches, region -> oldest
- [x] One-tap outcome logging + callback due_date reminders
- [x] Pipeline status transitions
- **Acceptance:** call a test lead, log outcome, callback reappears on date. ✅ Verified (appointment removes from queue; callback creates due activity).

## Phase 3 — Map
- [x] `/map` dots-only view (Leaflet + OSM) — ✅ live-tested
- [x] Geocode action (Nominatim, PLZ fallback) — ✅ live-tested
- [x] ORS isochrones (rate-safe, DB cache, quota status line) — ✅ live-tested; fixed stale-cache bug
- **Acceptance:** upload sample, geocode empties, trigger rate-limited isochrone run. ✅ All three verified live.

## Phase 4 — Gmail (deferred)
- [x] OAuth client flow (gmail.readonly) — coded, mocked-verified; needs real creds
- [x] Poller -> inbound activity + Replied badge — coded, mocked-verified
- [~] Live test with real Google Cloud OAuth client (user provides Client ID/Secret)
- **Acceptance:** reply to test email surfaces on lead.

## Phase 5 — Reporting
- [x] Daily/region outcome reports + pipeline counts + callback due list + Today summary
- [x] EOD export (semicolon + BOM, German Excel / SharePoint friendly)
- [x] CSV export on any list (leads, honoring filters)
- **Acceptance:** report numbers match logged activities. ✅ Verified (badges, exports with BOM + `;`).

## Phase 6 — Data load
- [x] Import ~800 + ~250 real CSVs, run dedup, verify counts, snapshot
- [x] Add `responsible` (owner) field to leads, populated from `Responsible` column of the master export
- **Acceptance:** counts match source, no data loss. ✅ Imported: 1027 companies, 1054 leads, 1103 locations, 975 contacts; 0 duplicate leads; `responsible` shown on leads list/detail/export.

## Phase 7 — Docs freeze
- [x] Final changelog, PROGRESS handoff, README polish
- **Acceptance:** `PROGRESS.md` fully describes state for next agent. ✅ Done — docs reflect all phases; deferred items tracked in PROGRESS/PHASES.

## Phase 8 — Auth, user profiles, HTTPS
- [x] Login/logout app-wide (Flask-Login) + CSRF on every POST (Flask-WTF)
- [x] Maptool-V3-style login lockout (cadence ~15/min sliding window + persisted per-user lock, admin unlock)
- [x] Roles admin + user; admin-only Users page (create/disable/unlock/reset), Settings, Import/Matches
- [x] Per-user lead visibility (`leads.responsible` == display name; admin sees all) across Leads/Today/Dashboard/Reports/Map/exports
- [x] Profile page (display name + password); `flask create-user` CLI
- [x] HTTPS: Waitress (`serve.py`) + Caddy reverse proxy (`Caddyfile`, tls internal) + `start-secure.bat`; ProxyFix; Secure cookie behind proxy; SECRET_KEY not hardcoded
- **Acceptance:** anon redirected to login; wrong-password lockout after ~15 attempts blocks even correct pw; user sees only own leads (foreign lead 404); all routes 200 over https://localhost:4443; dev `run.py` still works. ✅ Verified live (admin + user + lockout + CSRF + HTTPS + visibility).

## Deferred (see blueprint §15) — do NOT miss
- [ ] Acquisition pipeline tracking: persist the 37 step-date columns (`01. First contact` ... `21. Signed contract distributed`) + Last Status / Entrypoint / Status / Acquisition Status+Progress per company; UI progress + reporting; survives re-exports (dedupe). Test file: `data/test/test_rich_export.tsv`.
- [ ] Blocked leads via isochrones: build our OWN blocklist from the map — flag leads outside our driving-time operating range (ORS 20/30-min isochrones) as `blocked`; threshold setting in Settings; blocked status already excluded from Today.