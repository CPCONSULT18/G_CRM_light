@echo off
setlocal
cd /d "%~dp0"
if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

set LEADFLOW_COOKIE_SECURE=1
echo Starting LeadFlow CRM (Waitress + Caddy)...
echo Open https://localhost:4443  (trust the local Caddy root CA if prompted)

start "LeadFlow Caddy" caddy run --config Caddyfile
python serve.py
