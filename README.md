# G_CRM_light — LeadFlow CRM

Self-hosted, single-user light CRM for cold outreach: CSV import (blocklist + sourced leads), relational database, auto-dedup matching, daily call queue with reminders, one-tap outcome logging, light reporting, and a Germany map module (geocoding + driving isochrones).

## Quick start
1. `pip install -r requirements.txt`
2. `start.bat`
3. Open `http://localhost:5000`

## Docs
- `implementation_blueprint.md` — the full plan
- `PROGRESS.md` — live status ("where we are / stopped / next")
- `PHASES.md` — phase checklist
- `CHANGELOG.md` — dated changes
- `AGENTS.md` — handoff conventions for contributors/agents

## Data & privacy
All data stays local in `data/leadflow.db`. Client CSVs and secrets are gitignored — never commit them.