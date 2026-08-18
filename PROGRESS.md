# PROGRESS.md — LeadFlow CRM

> Single source of truth for "where we are / where we stopped / what's next / blockers".
> Updated at the end of every working session. **Any agent: read this file first.**

## Current state
**Phase 8 (auth, user profiles, HTTPS) done and verified.** Phases 0, 1, 2, 3, 5, 6, 7 done; Phase 4 coded + mocked-verified (needs real Google Cloud OAuth creds).

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

## Phase 6 import summary
- Imported (idempotent, source labels = clear file names):
  - `WOL.csv` -> source `WOL` (9 leads) — Wolfsburg research file.
  - `BWBA.csv` -> source `BWBA` (109 leads) — Ulm/Süd research file (uses `Investor (Dealer & Brands)` header; company keyword precedence fixed so `Investor` beats `Group`).
  - `Maike\Calw.csv` -> `Maike-Calw` (23), `Maike\Heilbronnfull.csv` + `Heilbronn.csv` -> `Maike-Heilbronn` (113), `Maike\Offenburg.csv` -> `Maike-Offenburg` (15), `Maike\Villingen-Schwenningenfull.csv` -> `Maike-VS` (18).
  - `Han\HAN.csv` + `HAN - Kopie.csv` -> `HAN` (94, Kopie deduped by idempotency).
  - `ORIGINALG.csv` -> `OriginalG` (673) — the "other" master file; contains the `Responsible` column (Lei/Willy/Erik/Jan/Thomas/Maike/Christian/Philipp) now stored in `leads.responsible`.
- Totals: **1027 companies, 1054 leads, 1103 locations, 975 contacts**, 41 regions. Status: 875 `new`, 179 `blocked`. 0 duplicate leads (company+region+source).
- Encoding note: OriginalG.csv is latin-1 (umlauts decode correctly); other files are UTF-8 with BOM.

## Where we stopped
- Phase 8 done and verified (auth, user profiles, HTTPS). Remaining: Phase 4 live Gmail test (needs Google Cloud creds), then any future/roadmap work.

## What is next (in order)
1. **Phase 4 live**: user creates Google Cloud OAuth client (Desktop app, scope gmail.readonly), pastes Client ID/Secret in Settings -> Connect -> Poll. Steps documented in README/blueprint §8. (Auth/HTTPS is in place; the callback redirect URI is now `https://<host>:4443/gmail/callback`.)
2. **HTTPS hardening when going to internet/VPS**: change Caddyfile from `https://localhost:4443` + `tls internal` to the real domain + `tls` (Let's Encrypt), open 443, keep Waitress on 127.0.0.1:5000.
3. Roadmap — deferred items (blueprint §15): acquisition pipeline tracking, isochrone-based blocking.

## Blockers
- Gmail live test needs Google Cloud OAuth client (user action).

## GitHub push status
- Local commits ahead of origin/main (Phases 0-1, 2, rich-layout, docs+geocode-test, isochrones fix, reporting, gmail, data load). User handles pushes.

## Key decisions (for continuity)
- No separate `tasks` table: reminders are `activities` with `due_date` + status.
- Contact at Dealer is ONE cell -> regex extraction (email, phone, remainder = name).
- Data stays local; blocklist + lead CSV layout is the dealer layout in blueprint §5.
- Accent color `#C5B358` reserved for high-impact CTAs/underlines/badges only.
- Default country code for phone normalization = 49 (Germany), editable in Settings.
- Lead = one row in the dealer CSV; company = unique Investor (Group) name.
- `responsible` (owner) comes from the `Responsible` column of OriginalG.csv only; research files leave it empty.
- `OriginalG.csv` is the "other" master file (not the user's research); research files carry region-specific source labels.
- **Auth**: roles are admin + user only. A normal user's visibility = leads where `leads.responsible` == their display name (admin sees all). Set the display name to the exact `Responsible` value when creating users.
- **Login lockout follows MAPTOOL3 cadence**: sequential attempts, ~15/min sliding window; on overflow the account is locked 15 min (persisted in `users.locked_until`). Settings keys `login_max_attempts`, `login_window_seconds`, `login_lock_seconds`.
- **Serving**: dev = `python run.py` (plain HTTP localhost). Secure = `start-secure.bat` -> Waitress on 127.0.0.1:5000 behind Caddy (TLS internal, https://localhost:4443). `LEADFLOW_COOKIE_SECURE=1` is set by start-secure.bat only. SECRET_KEY auto-generated to `data/secret_key` or `LEADFLOW_SECRET` env.

## Deferred (see blueprint §15) — do NOT miss
- Acquisition pipeline tracking: persist the 37 step-date columns (`01. First contact` ... `21. Signed contract distributed`) + Last Status / Entrypoint / Status / Acquisition Status+Progress per company; UI progress + reporting; survives re-exports (dedupe). Test file: `data/test/test_rich_export.tsv`.
- Blocked leads via isochrones: build our OWN blocklist from the map — flag leads outside our driving-time operating range (ORS 20/30-min isochrones) as `blocked`; threshold setting in Settings; blocked status already excluded from Today.

## Future ideas
- (none recorded yet)