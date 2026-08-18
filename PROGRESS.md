# PROGRESS.md — LeadFlow CRM

> Single source of truth for "where we are / where we stopped / what's next / blockers".
> Updated at the end of every working session. **Any agent: read this file first.**

## Current state
**Phase 1 complete and verified.** Phase 0 complete. Phase 2 (Today queue polish) next.

## What is done
- Phase 0 fully: repo cloned, git identity set, MAPTOOL3 heritage copied to `app/map/heritage/`, docs written, scaffold pushed.
- Phase 1 fully: Flask app skeleton (factory + 6 blueprints), DB schema + settings seed, importer (dealer layout, contact-cell regex parser, latin-1/UTF-8 autodetect, Investor grouping), matching engine (hard/probable/soft), import UI with preview, match review, lead list + detail + outcome logging. Visual identity theme.css + base templates.
- **Verified end-to-end:** imported a 7-row test leads CSV + 4-row blocklist; importer grouped 7 rows -> 5 companies / 7 locations / 5 contacts / 7 leads; matcher produced hard(6)/probable(5)/soft(4) with correct rules; all pages return 200; outcome POST creates activity with due_date and flips lead status to callback. DB reset to clean state after tests.

## Where we stopped
- After verifying Phase 1. Test CSVs remain at `data/test/test_leads.csv` and `data/test/test_blocklist.csv` for reuse. DB was wiped of test data (schema intact).

## What is next (in order)
1. **Phase 2 — Today queue** (dedicated `/today` view: leads minus hard matches, sorted region -> oldest, one-tap outcomes, callbacks reappearing on due_date). Core logging already exists on the lead detail page.
2. Phase 3 — Map: dots-only confirmed working; geocode + isochrones implemented, needs live API test.
3. Phase 4 — Gmail OAuth + reply poller.
4. Phase 5 — Reporting polish + EOD export (basic version exists).
5. Phase 6 — Import real CSVs (~800, ~250) once provided by user.
6. Phase 7 — Docs freeze.

## Blockers
- None. Tested with local test data.
- Pending from user (not blocking): real CSVs (~800, ~250); ORS API key for isochrones; Google Cloud project for Gmail (Phase 4).
- GitHub push needs credential prompt once (repo is public, read-only works).

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