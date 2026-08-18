# PROGRESS.md — LeadFlow CRM

> Single source of truth for "where we are / where we stopped / what's next / blockers".
> Updated at the end of every working session. **Any agent: read this file first.**

## Current state
**Phase 4 (Gmail) coded + mocked-e2e verified; needs real Google Cloud OAuth creds to go live.** Phases 0, 1, 2, 3, 5 done. Phase 6 (data load) and 7 (docs freeze) pending.

## What is done
- Phase 0 fully: repo cloned, git identity set, MAPTOOL3 heritage copied to `app/map/heritage/`, docs written, scaffold pushed.
- Phase 1 fully: Flask app skeleton (factory + 6 blueprints), DB schema + settings seed, importer (dealer layout, contact-cell regex parser, latin-1/UTF-8 autodetect, **idempotent** Investor grouping), matching engine (hard/probable/soft), import UI with preview, match review, lead list + detail + outcome logging. Visual identity theme.css + base templates.
- Phase 2 fully: dedicated **Today queue** (`/today`): callbacks due + fresh queue (hard matches AND replied leads excluded), region->oldest. Outcome logging flips lead status. Verified.
- **Rich SharePoint export layout supported** (importer): 38-column tab-separated files import cleanly; `Blocked by signed dealer?` = `Block` sets lead status `blocked` (excluded from Today). Verified.
- **Phase 3 (Map) verified live**: dots-only + geocoding (Nominatim, PLZ fallback) + isochrones (ORS v2, 20/30-min, DB cache). Fixed stale-cache bug. ORS key stored locally.
- **Phase 5 (Reporting) complete**: Today summary badges; activity by day + by region; pipeline counts; callbacks due; EOD export (`;` + BOM, German Excel/SharePoint); leads CSV export honoring filters. Verified.
- **Phase 4 (Gmail) coded + mocked-verified**: OAuth flow (gmail.readonly, token at `data/gmail_token.json`), reply poller matching sender email/domain to contacts -> `email/replied` activity, dedupe via `activities.gmail_msg_id` (migration added), "Replied" badge on leads/Today, replied leads excluded from Today queue, Connect/Poll/Disconnect in Settings. Verified with mocked API; **needs real Google Cloud OAuth client to test live.**

## Where we stopped
- Phase 4 verified with mocked API. DB reset to clean state. Real Gmail test blocked on Google Cloud OAuth client credentials from user.

## What is next (in order)
1. **Phase 4 live**: user creates Google Cloud OAuth client (Desktop app, scope gmail.readonly), pastes Client ID/Secret in Settings -> Connect -> Poll. Steps documented in README/blueprint §8.
2. Phase 6 — Import real CSVs (~800, ~250) once provided by user.
3. Phase 7 — Docs freeze.

## Blockers
- Gmail live test needs Google Cloud OAuth client (user action).
- Pending from user (not blocking): real CSVs (~800, ~250).

## GitHub push status
- Local commits ahead of origin/main (Phases 0-1, 2, rich-layout, docs+geocode-test, isochrones fix, reporting, gmail). User handles pushes.

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