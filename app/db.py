import os
import sqlite3
from pathlib import Path

import click
from flask import current_app, g

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "leadflow.db"

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS companies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT NOT NULL,
    region      TEXT,
    source      TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS locations (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id     INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    address        TEXT,
    city           TEXT,
    plz            TEXT,
    lat            REAL,
    lng            REAL,
    phone          TEXT,
    iso_json       TEXT,
    geocode_status TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS contacts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    name        TEXT,
    email       TEXT,
    phone       TEXT,
    notes       TEXT
);

CREATE TABLE IF NOT EXISTS leads (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id  INTEGER REFERENCES companies(id) ON DELETE CASCADE,
    source      TEXT,
    region      TEXT,
    qual_score  INTEGER DEFAULT 0,
    status      TEXT DEFAULT 'new',
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS opportunities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id     INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    stage       TEXT DEFAULT 'interested',
    value       REAL,
    notes       TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS activities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id     INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    type        TEXT DEFAULT 'call',
    outcome     TEXT,
    notes       TEXT,
    due_date    TEXT,
    status      TEXT DEFAULT 'done',
    gmail_msg_id TEXT,
    occurred_at TEXT DEFAULT (datetime('now')),
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS contacted (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT,
    email       TEXT,
    phone       TEXT,
    domain      TEXT,
    source      TEXT,
    note        TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS matches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id     INTEGER REFERENCES leads(id) ON DELETE CASCADE,
    contacted_id INTEGER REFERENCES contacted(id) ON DELETE CASCADE,
    field       TEXT,
    confidence  TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    UNIQUE(lead_id, contacted_id, field)
);

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE INDEX IF NOT EXISTS idx_locations_company   ON locations(company_id);
CREATE INDEX IF NOT EXISTS idx_contacts_company    ON contacts(company_id);
CREATE INDEX IF NOT EXISTS idx_contacts_email      ON contacts(email);
CREATE INDEX IF NOT EXISTS idx_contacts_phone      ON contacts(phone);
CREATE INDEX IF NOT EXISTS idx_leads_company       ON leads(company_id);
CREATE INDEX IF NOT EXISTS idx_activities_lead     ON activities(lead_id);
CREATE INDEX IF NOT EXISTS idx_activities_gmail    ON activities(gmail_msg_id);
CREATE INDEX IF NOT EXISTS idx_matches_lead        ON matches(lead_id);
CREATE INDEX IF NOT EXISTS idx_contacted_email     ON contacted(email);
CREATE INDEX IF NOT EXISTS idx_contacted_phone     ON contacted(phone);
CREATE INDEX IF NOT EXISTS idx_contacted_domain    ON contacted(domain);
"""

DEFAULT_SETTINGS = {
    "country_code": "49",
    "ors_api_key": "",
    "ors_free_daily_limit": "500",
    "gmail_token_path": "",
    "gmail_client_id": "",
    "gmail_client_secret": "",
    "gmail_user": "",
}

# Column migrations applied to pre-existing databases (idempotent).
MIGRATIONS = [
    ("activities", "gmail_msg_id", "TEXT"),
]


def get_db():
    if "db" not in g:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        g.db = conn
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _apply_migrations(conn):
    for table, column, coltype in MIGRATIONS:
        exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone()
        if not exists:
            continue
        cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
        if column not in cols:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {coltype}")


def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    _apply_migrations(conn)
    conn.executescript(SCHEMA)
    for key, value in DEFAULT_SETTINGS.items():
        conn.execute(
            "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value)
        )
    conn.commit()
    conn.close()


def get_setting(key, default=None):
    db = get_db()
    row = db.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if row:
        return row["value"]
    return default


def set_setting(key, value):
    db = get_db()
    db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    db.commit()


def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


@click.command("init-db")
def init_db_command():
    """Create the database schema and seed default settings."""
    init_db()
    click.echo(f"Initialized database at {DB_PATH}")