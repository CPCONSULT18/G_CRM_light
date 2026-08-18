# PROGRESS.md — LeadFlow CRM

> Single source of truth for "where we are / where we stopped / what's next / blockers".
> Updated at the end of every working session. **Any agent: read this file first.**

## Current state
**Phase 6 (data load) done: all real CSVs imported.** Phases 0, 1, 2, 3, 5 done; Phase 4 coded + mocked-verified (needs real Google Cloud OAuth creds); Phase 7 (docs freeze) pending.

## What is done
- Phase 0 fully: repo cloned, git identity set, MAPTOOL3 heritage copied to `app/map/heritage/`, docs written, scaffold pushed.
- Phase 1 fully: Flask app skeleton (factory + 6 blueprints), DB schema + settings seed, importer (dealer layout, contact-cell regex parser, latin-1/UTF-8 autodetect, **idempotent** Investor grouping), matching engine (hard/probable/soft), import UI with preview, match review, lead list + detail + outcome logging. Visual identity theme.css + base templates.
- Phase 2 fully: dedicated **Today queue** (`/today`): callbacks due + fresh queue (hard matches AND replied leads excluded), region->oldest. Outcome logging flips lead status. Verified.
- **Rich SharePoint export layout supported** (importer): 38-column tab-separated files import cleanly; `Blocked by signed dealer?` = `Block` sets lead status `blocked` (excluded from Today). Verified.
- **Phase 3 (Map) verified live**: dots-only + geocoding (Nominatim, PLZ fallback) + isochrones (ORS v2, 20/30-min, DB cache). Fixed stale-cache bug. ORS key stored locally.
- **Phase 5 (Reporting) complete**: Today summary badges; activity by day + by region; pipeline counts; callbacks due; EOD export (`;` + BOM, German Excel/SharePoint); leads CSV export honoring filters. Verified.
- **Phase 4 (Gmail) coded + mocked-verified**: OAuth flow (gmail.readonly, token at `data/gmail_token.json`), reply poller matching sender email/domain to contacts -> `email/replied` activity, dedupe via `activities.gmail_msg_id` (migration added), "Replied" badge on leads/Today, replied leads excluded from Today queue, Connect/Poll/Disconnect in Settings. Verified with mocked API; **needs real Google Cloud OAuth client to test live.**
- **Phase 6 (data load) done**: all real CSVs imported (see below). `responsible` field added to `leads` (from the `Responsible` column in OriginalG.csv), shown on leads list, lead detail, and leads CSV export.

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
- Phase 6 imported and verified. Remaining: Phase 4 live Gmail test (needs Google Cloud creds), Phase 7 docs freeze.

## What is next (in order)
1. **Phase 4 live**: user creates Google Cloud OAuth client (Desktop app, scope gmail.readonly), pastes Client ID/Secret in Settings -> Connect -> Poll. Steps documented in README/blueprint §8.
2. Phase 7 — Docs freeze (this file + CHANGELOG + PHASES finalized).

## Blockers
- Gmail live test needs Google Cloud OAuth client (user action).

## GitHub push status
- Local commits ahead of origin/main (Phases 0-1, 2, rich-layout, docs+geocode-test, isochrones fix, reporting, gmail). User handles pushes.

## Key decisions (for continuity)
- No separate `tasks` table: reminders are `activities` with `due_date` + status.
- Contact at Dealer is ONE cell -> regex extraction (email, phone, remainder = name).
- Data stays local; blocklist + lead CSV layout is the dealer layout in blueprint §5.
- Accent color `#C5B358` reserved for high-impact CTAs/underlines/badges only.
- Default country code for phone normalization = 49 (Germany), editable in Settings.
- Lead = one row in the dealer CSV; company = unique Investor (Group) name.
- `responsible` (owner) comes from the `Responsible` column of OriginalG.csv only; research files leave it empty.
- `OriginalG.csv` is the "other" master file (not the user's research); research files carry region-specific source labels.

## Blockers
- None currently.
- Pending from user (not blocking): real CSVs (~800, ~250) for Phase 6; ORS API key for isochrones (dots-only until provided); Google Cloud project for Gmail (Phase 4).
- `git ls-remote`/push may prompt for credentials once; user confirmed repo is public.

## Key decisions (for continuity)
- No separate `tasks` table: reminders are `activities` with `due_date` + status.
- Contact at Dealer is ONE cell -> regex extraction (email, phone, remainder = name).
- Data stays local; blocklist + lead CSV layout is the dealer layout in blueprint §5.
- Accent color `#C5B358` reserved for high-impact CTAs/underlines/badges only.