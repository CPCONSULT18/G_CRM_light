"""Gmail integration: OAuth (gmail.readonly) + reply poller (Phase 4)."""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from .db import data_dir, db_path, get_db, get_setting, set_setting

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"

# ISO-8601 (with timezone) >= this -> treat as reply (created after CRM start).
MIN_CREATED = "2026-01-01T00:00:00Z"

TOKEN_FILE = data_dir() / "gmail_token.json"


def token_path():
    return TOKEN_FILE


def _client():
    cid = get_setting("gmail_client_id")
    secret = get_setting("gmail_client_secret")
    if not cid or not secret:
        return None, None
    return cid, secret


def build_auth_url(redirect_uri):
    """Return the Google consent URL for the user to visit."""
    cid, _ = _client()
    import urllib.parse

    params = {
        "client_id": cid,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "consent",
    }
    return AUTH_URL + "?" + urllib.parse.urlencode(params)


def exchange_code(code, redirect_uri):
    """Exchange the OAuth code for tokens; save to token file. Returns email."""
    cid, secret = _client()
    r = requests.post(
        TOKEN_URL,
        data={
            "client_id": cid,
            "client_secret": secret,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
        timeout=30,
    )
    r.raise_for_status()
    token = r.json()
    token["client_id"] = cid
    token["client_secret"] = secret
    TOKEN_FILE.write_text(json.dumps(token), encoding="utf-8")
    set_setting("gmail_token_path", str(TOKEN_FILE))
    return _email_from_token(token)


def load_credentials():
    if not TOKEN_FILE.exists():
        return None
    try:
        token = json.loads(TOKEN_FILE.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    creds = Credentials(
        token=token.get("token"),
        refresh_token=token.get("refresh_token"),
        token_uri=TOKEN_URL,
        client_id=token.get("client_id"),
        client_secret=token.get("client_secret"),
        scopes=SCOPES,
    )
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _save_token(creds)
    return creds


def _save_token(creds):
    token = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
    }
    TOKEN_FILE.write_text(json.dumps(token), encoding="utf-8")


def _email_from_token(token):
    try:
        r = requests.get(
            f"{GMAIL_API}/profile",
            headers={"Authorization": f"Bearer {token.get('token')}"},
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("emailAddress", "")
    except requests.RequestException:
        pass
    return ""


def revoke_token():
    if TOKEN_FILE.exists():
        try:
            TOKEN_FILE.unlink()
        except OSError:
            pass
    set_setting("gmail_user", "")
    set_setting("gmail_token_path", "")


def _authed_get(url, creds):
    return requests.get(url, headers={"Authorization": f"Bearer {creds.token}"}, timeout=30)


def poll_replies():
    """Fetch recent inbox threads that replied to our sent mail.

    Strategy (no sent-mail analysis): list inbox messages, match sender
    domain against contacts' email domains, create inbound activities.
    """
    creds = load_credentials()
    if creds is None:
        return 0, 0, "Not connected"

    db = get_db()
    created = 0
    seen = 0

    # Messages from the inbox, newest first.
    r = _authed_get(f"{GMAIL_API}/messages?maxResults=50&q=in:inbox newer_than:14d", creds)
    if r.status_code != 200:
        return 0, 0, f"API error {r.status_code}: {r.text[:120]}"
    listing = r.json().get("messages", [])
    if not listing:
        return 0, 0, "No inbox messages in the last 14 days"

    # Map email -> lead via contacts (exact or domain match).
    leads_for = {}
    for c in db.execute(
        "SELECT c.email, l.id AS lead_id FROM contacts c "
        "JOIN companies co ON co.id = c.company_id "
        "JOIN leads l ON l.company_id = co.id "
        "WHERE c.email IS NOT NULL AND c.email != ''"
    ).fetchall():
        leads_for.setdefault(c["email"].strip().lower(), set()).add(c["lead_id"])

    for item in listing[:50]:
        mid = item.get("id", "")
        if not mid:
            continue
        # Skip already-imported messages.
        dup = db.execute(
            "SELECT id FROM activities WHERE gmail_msg_id = ?", (mid,)
        ).fetchone()
        if dup:
            continue

        msg = _authed_get(f"{GMAIL_API}/messages/{mid}?format=metadata&metadataHeaders=From", creds)
        if msg.status_code != 200:
            continue
        meta = msg.json()
        headers = {h["name"].lower(): h["value"] for h in meta.get("payload", {}).get("headers", [])}
        sender = headers.get("from", "")
        if not sender:
            continue
        sender_email = _extract_email(sender)
        if not sender_email:
            continue

        snippet = meta.get("snippet", "")[:300]
        date_raw = meta.get("internalDate", "")
        when = _fmt_date(date_raw)

        # Find matching leads: exact email first, then domain.
        targets = leads_for.get(sender_email.lower(), set())
        if not targets:
            sdom = _base(sender_email)
            for cemail, lids in leads_for.items():
                if sdom and _base(cemail) == sdom:
                    targets |= lids
        seen += 1
        if not targets:
            continue

        for lead_id in targets:
            db.execute(
                "INSERT INTO activities (lead_id, type, outcome, notes, status, occurred_at, gmail_msg_id) "
                "VALUES (?, 'email', 'replied', ?, 'done', ?, ?)",
                (lead_id, f"Reply from {sender} — {snippet}", when, mid),
            )
            created += 1
        db.commit()

    return created, seen, "ok"


def _extract_email(sender):
    import re

    m = re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", sender)
    return m.group(0).lower() if m else ""


def _base(email):
    from .normalize import base_domain

    return base_domain(email)


def _fmt_date(internal_ms):
    try:
        dt = datetime.fromtimestamp(int(internal_ms) / 1000, tz=timezone.utc)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError, OverflowError):
        return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
