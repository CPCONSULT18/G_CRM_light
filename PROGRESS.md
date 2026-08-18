# PROGRESS.md — LeadFlow CRM

> Single source of truth for "where we are / where we stopped / what's next / blockers".
> Updated at the end of every working session. **Any agent: read this file first.**

## Current state
**Phase 3 (Map) COMPLETE — all three sub-features live-tested.** Phases 0-2 complete.

## What is done
- Phase 0 fully: repo cloned, git identity set, MAPTOOL3 heritage copied to `app/map/heritage/`, docs written, scaffold pushed.
- Phase 1 fully: Flask app skeleton (factory + 6 blueprints), DB schema + settings seed, importer (dealer layout, contact-cell regex parser, latin-1/UTF-8 autodetect, **idempotent** Investor grouping), matching engine (hard/probable/soft), import UI with preview, match review, lead list + detail + outcome logging. Visual identity theme.css + base templates.
- Phase 2 fully: dedicated **Today queue** (`/today`): callbacks due (activity due_date <= today) + fresh queue (status new/called/no_answer/voicemail, hard matches excluded), region->oldest. Outcome logging flips lead status (callback/appointment/won/lost/not_interested/called). Verified: appointment logs and removes lead from queue; callback creates due_date activity.
- **Rich SharePoint export layout supported** (importer): 38-column tab-separated files import cleanly; `Blocked by signed dealer?` column value `Block` sets lead status `blocked` (excluded from Today queue). Verified with a real export row, marked source `test`.
- **Phase 3 (Map) verified live:**
  - Dots-only view: `/map` + `/map/locations` markers with popups.
  - Geocoding (`/map/geocode`): Nominatim address -> PLZ fallback, 1.1s delay, 429 handling. Verified München address + PLZ-only fallback.
  - **Isochrones (`/map/isochrones`): ORS v2, 20-min + 30-min driving-car, DB cache in `iso_json`, rate-safe batches. Verified live with working ORS key: both iso caches persist, second run skips cached instantly. Fixed stale-cache bug (20-min overwrote 30-min).**

## Where we stopped
- Phase 3 complete. DB reset to clean state after tests. ORS key stored locally in Settings (never committed).

## What is next (in order)
1. Phase 4 — Gmail OAuth + reply poller (needs Google Cloud project; deferred).
2. Phase 5 — Reporting polish + EOD export (basic version exists).
3. Phase 6 — Import real CSVs (~800, ~250) once provided by user.
4. Phase 7 — Docs freeze.

## Blockers
- None for core. ORS key now configured and verified.
- Pending from user (not blocking): real CSVs (~800, ~250); Google Cloud project for Gmail (Phase 4).

## GitHub push status
- Local commits ahead of origin/main (Phases 0-1, 2, rich-layout, docs+geocode-test, isochrones fix). User handles pushes.

## Key decisions (for continuity)
- No separate `tasks` table: reminders are `activities` with `due_date` + status.
- Contact at Dealer is ONE cell -> regex extraction (email, phone, remainder = name).
- Data stays local; blocklist + lead CSV layout is the dealer layout in blueprint §5.
- Accent color `#C5B358` reserved for high-impact CTAs/underlines/badges only.
- Default country code for phone normalization = 49 (Germany), editable in Settings.
- Lead = one row in the dealer CSV; company = unique Investor (Group) name.

## Blockers
- None currently.
- Pending from user (not blocking): real CSVs (~800, ~250) for Phase 6; ORS API key for isochrones (dots-only until provided); Google Cloud project for Gmail (Phase 4).
- `git ls-remote`/push may prompt for credentials once; user confirmed repo is public.

## Key decisions (for continuity)
- No separate `tasks` table: reminders are `activities` with `due_date` + status.
- Contact at Dealer is ONE cell -> regex extraction (email, phone, remainder = name).
- Data stays local; blocklist + lead CSV layout is the dealer layout in blueprint §5.
- Accent color `#C5B358` reserved for high-impact CTAs/underlines/badges only.