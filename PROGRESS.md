# PROGRESS.md — LeadFlow CRM

> Single source of truth for "where we are / where we stopped / what's next / blockers".
> Updated at the end of every working session. **Any agent: read this file first.**

## Current state
**Phase 3 (Map) in progress — geocoding done and live-tested; isochrones coded but need an ORS key to test.** Phases 0-2 complete.

## What is done
- Phase 0 fully: repo cloned, git identity set, MAPTOOL3 heritage copied to `app/map/heritage/`, docs written, scaffold pushed.
- Phase 1 fully: Flask app skeleton (factory + 6 blueprints), DB schema + settings seed, importer (dealer layout, contact-cell regex parser, latin-1/UTF-8 autodetect, **idempotent** Investor grouping), matching engine (hard/probable/soft), import UI with preview, match review, lead list + detail + outcome logging. Visual identity theme.css + base templates.
- Phase 2 fully: dedicated **Today queue** (`/today`): callbacks due (activity due_date <= today) + fresh queue (status new/called/no_answer/voicemail, hard matches excluded), region->oldest. Outcome logging flips lead status (callback/appointment/won/lost/not_interested/called). Verified: appointment logs and removes lead from queue; callback creates due_date activity.
- **Rich SharePoint export layout supported** (importer): 38-column tab-separated files import cleanly; `Blocked by signed dealer?` column value `Block` sets lead status `blocked` (excluded from Today queue). Verified with a real export row, marked source `test`.
- **Phase 3 partial — geocoding live-tested**: `/map/geocode` (Nominatim, address query -> PLZ fallback, 1.1s delay, 429 handling). Verified: address geocode ok, PLZ fallback ok, `/map/locations` markers return points, `/map` renders 200.

## Where we stopped
- After live-testing geocoding. DB reset to clean state. Test CSVs at `samples/sample_leads.csv` + `samples/sample_blocklist.csv`; rich export at `data/test/test_rich_export.tsv`.

## What is next (in order)
1. Phase 3 — isochrones: code exists (`/map/isochrones`, ORS v2, 20/30-min, batches of 5, 15s pause, DB cache, 429 retry). Needs an ORS API key pasted in Settings to live-test. Dots-only + geocode confirmed working without key.
2. Phase 4 — Gmail OAuth + reply poller.
3. Phase 5 — Reporting polish + EOD export (basic version exists).
4. Phase 6 — Import real CSVs (~800, ~250) once provided by user.
5. Phase 7 — Docs freeze.

## Blockers
- ORS API key not provided -> isochrones untested (dots-only + geocoding work fine without it).
- Pending from user (not blocking): real CSVs (~800, ~250); Google Cloud project for Gmail (Phase 4).

## GitHub push status
- Local commits ahead of origin/main (Phases 0-1, 2, rich-layout, docs+geocode-test). User handles pushes.

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