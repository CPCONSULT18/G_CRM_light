# AGENTS.md — LeadFlow CRM handoff conventions

For any agent working on this repo (human or AI).

## First step
Read `PROGRESS.md`. It is the single source of truth for current state, next steps, and blockers. Then read `PHASES.md` and this file.

## Rules
1. **Never commit to `main` directly without checking `git status` and `git log` first.** Commit with concise messages matching repo style (see `git log --oneline`).
2. **Keep docs live.** After any phase of work:
   - Update `PROGRESS.md` (state, stopped, next, blockers).
   - Add a dated entry to `CHANGELOG.md`.
   - Tick/untick `PHASES.md` checkboxes honestly (only tick what is verified).
3. **Verify before marking done.** A phase/feature is "done" only when the app runs and behavior is confirmed (run server, import test CSV, inspect DB rows).
4. **No feature creep.** Scope is frozen per the blueprint §0. New ideas go into `PROGRESS.md` under "Future ideas", not into code.
5. **Data stays local.** Never upload `data/leadflow.db` or client CSVs to the repo. `.gitignore` must exclude `data/`, `*.csv` with real client data, and secrets.
6. **Visual identity is strict** (blueprint §11): bg `#1A1A1B`, text `#F5F5F2`, accent `#C5B358` reserved for high-impact CTAs/underlines/badges, 1px hairline borders only, generous whitespace, "carved" text feel. `theme.css` is the single source.
7. **Gmail/OAuth secrets and ORS API keys** go in `data/settings` or local files, never committed.

## Structure
- `app/` — Flask application (factory in `app/__init__.py`, schema in `app/db.py`)
- `app/templates/`, `app/static/` — server-rendered UI + `theme.css`
- `app/map/heritage/` — MAPTOOL3 original files (reference only; port, don't edit here)
- `data/` — SQLite DB + runtime (gitignored)
- `docs/` — reference material (MAPTOOL3 plans)
- `implementation_blueprint.md`, `CHANGELOG.md`, `PHASES.md`, `PROGRESS.md`, `README.md`, `AGENTS.md` — root docs

## Test command
`start.bat` (or `python run.py`) -> open `http://localhost:5000`.