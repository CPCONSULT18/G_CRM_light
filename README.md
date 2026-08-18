# G_CRM_light — LeadFlow CRM

Self-hosted light CRM for cold outreach: CSV import (blocklist + sourced leads), relational database, auto-dedup matching, daily call queue with reminders, one-tap outcome logging, light reporting, a Germany map module (geocoding + driving isochrones), login + user profiles, and HTTPS.

## Quick start (dev)
1. `pip install -r requirements.txt`
2. `python run.py` (first run creates the DB; then `python -m flask --app run.py create-user --email you@x.com --name YourName --role admin` to create the first account)
3. Open `http://localhost:5000` and sign in.

## Production / LAN (HTTPS)
1. Install Caddy (e.g. `winget install CaddyServer.Caddy`).
2. `start-secure.bat` — starts Waitress (`serve.py`, 127.0.0.1:5000) + Caddy reverse proxy with a locally-trusted cert.
3. Open `https://localhost:4443` (trust the local Caddy root CA the first time). Other devices on the LAN use `https://<this-machine>:4443`.
4. Going public: in `Caddyfile` replace `https://localhost:4443` + `tls internal` with your domain + `tls` (Let's Encrypt) and open 443.

## Users & roles
- `flask create-user` (or the Users page, admin-only) creates accounts. Roles: **admin** (everything) and **user** (only leads where `responsible` == their display name).
- Login is rate-limited Maptool-V3 style (~15 attempts/min); after overflow an account locks for 15 min. Admins can unlock in Users.
- Gmail OAuth in Settings is admin-only; its redirect URI is now `https://<host>:4443/gmail/callback`.

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

## Backup & restore

**GitHub = code fallback.** The full app + docs live on `github.com/CPCONSULT18/G_CRM_light` (tagged releases at `v0.6.0`, …). To restore on a fresh machine:

```bat
git clone https://github.com/CPCONSULT18/G_CRM_light.git
cd G_CRM_light
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
flask --app run.py init-db
flask --app run.py create-user --email you@x.com --name YourName --role admin
start-secure.bat        (or: python run.py, then open http://localhost:5000)
```

Order matters: run `init-db` before `create-user` (a fresh clone has no `users` table yet).

**Data stays local.** The CRM database is intentionally not on GitHub. Back it up with `backup.bat`, which copies `data/leadflow.db` to `C:\Users\Lenovo\Desktop\LEADFLOW_backups\` (timestamped). Restore = copy a backup file back to `data\leadflow.db` (stop the app first).