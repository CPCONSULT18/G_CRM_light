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

## Gmail reply detection (Phase 4)
1. Google Cloud Console -> create a project -> enable **Gmail API**.
2. Create an OAuth client ID of type **Desktop app** (scope `gmail.readonly`).
3. Paste Client ID + Client Secret into Settings -> Gmail -> Save.
4. Click **Connect Gmail**, approve in browser (token saved locally to `data/gmail_token.json`, never committed).
5. Click **Poll for replies** whenever you want to import inbound replies. Matches are by exact contact email or email domain; each reply creates an `email/replied` activity and a "replied" badge; replied leads leave the Today queue.

## Data & privacy
All data stays local in `data/leadflow.db`. Client CSVs, Gmail tokens, and API keys are gitignored — never commit them.