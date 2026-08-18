# PROGRESS.md — LeadFlow CRM

> Single source of truth for "where we are / where we stopped / what's next / blockers".
> Updated at the end of every working session. **Any agent: read this file first.**

## Current state
**Phase 2 complete and verified.** Phase 0, 1, 2 done. Phase 3 (Map live test) next.

## What is done
- Phase 0 fully: repo cloned, git identity set, MAPTOOL3 heritage copied to `app/map/heritage/`, docs written, scaffold pushed.
- Phase 1 fully: Flask app skeleton (factory + 6 blueprints), DB schema + settings seed, importer (dealer layout, contact-cell regex parser, latin-1/UTF-8 autodetect, **idempotent** Investor grouping), matching engine (hard/probable/soft), import UI with preview, match review, lead list + detail + outcome logging. Visual identity theme.css + base templates.
- Phase 2 fully: dedicated **Today queue** (`/today`): callbacks due (activity due_date <= today) + fresh queue (status new/called/no_answer/voicemail, hard matches excluded), region->oldest. Outcome logging flips lead status (callback/appointment/won/lost/not_interested/called). Verified: appointment logs and removes lead from queue; callback creates due_date activity.
- **Rich SharePoint export layout supported** (importer): 38-column tab-separated files import cleanly; `Blocked by signed dealer?` column value `Block` sets lead status `blocked` (excluded from Today queue). Verified with a real export row, marked source `test`.

## Where we stopped
- After verifying rich-layout import. DB reset to clean state after each test. Test CSVs at `samples/sample_leads.csv` + `samples/sample_blocklist.csv`; rich export at `data/test/test_rich_export.tsv`.

## What is next (in order)
1. Phase 3 — Map: code complete (dots-only + geocode + rate-safe isochrones); needs live test. No ORS key set -> runs dots-only.
2. Phase 4 — Gmail OAuth + reply poller.
3. Phase 5 — Reporting polish + EOD export (basic version exists).
4. Phase 6 — Import real CSVs (~800, ~250) once provided by user.
5. Phase 7 — Docs freeze.

## Blockers
- **GitHub push pending user auth** (see below).
- Pending from user (not blocking): real CSVs (~800, ~250); ORS API key; Google Cloud project for Gmail (Phase 4).

## GitHub push status
- Repo public; local commits ahead of origin/main (Phase 0-1 and Phase 2).
- `git push` hangs in this environment: Windows credential helper opens an interactive/GUI prompt that blocks a headless session. `credential.helper` set to `wincred` locally; stored `gh:github.com:CPCONSULT18` creds exist but may not cover git-over-https.
- **User can push with:** `cd C:\Users\Lenovo\Desktop\LEADFLOW && git push origin main` in their terminal, or provide a PAT / run `gh auth login`.

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