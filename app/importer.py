"""CSV importer for the dealer layout.

Expected header (semicolon or comma separated, with intentional empty columns):
    Metro Area/State; City; [empty]; [empty]; [empty];
    Investor (Group); Dealer Location Street; Dealer Location ZIP Code;
    [empty]; [empty]; Contact at Dealer (Name, Mail, Phone)

The importer auto-detects the delimiter, encoding, and column positions by
header keywords (falling back to positional defaults). 'Contact at Dealer'
is a single cell parsed into name / email / phone.
"""

import csv
import io
import re

from .db import get_db
from .normalize import parse_contact_cell

# Column header keywords -> internal field names.
HEADER_MAP = [
    ("region", ["metro", "area", "state", "bundesland"]),
    ("city", ["city", "ort"]),
    ("company", ["investor", "group", "firma", "company", "firm"]),
    ("address", ["dealer location street", "street", "strasse", "straße", "address"]),
    ("plz", ["zip", "plz", "postal", "postleitzahl"]),
    ("contact", ["contact at dealer", "contact", "kontakt"]),
]

POSITIONAL_DEFAULTS = {
    "region": 0,
    "city": 1,
    "company": 5,
    "address": 6,
    "plz": 7,
    "contact": 10,
}


def detect_encoding(raw):
    for enc in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            raw.decode(enc)
            return enc
        except (UnicodeDecodeError, ValueError):
            continue
    return "latin-1"


def detect_delimiter(header_line):
    candidates = [";", "\t", ","]
    counts = {d: header_line.count(d) for d in candidates}
    return max(counts, key=counts.get) if max(counts.values()) > 0 else ";"


def map_columns(header):
    """Return {field: col_index} by matching header keywords, else position."""
    mapping = {}
    lowered = [h.strip().lower() for h in header]
    for field, keywords in HEADER_MAP:
        idx = None
        for i, h in enumerate(lowered):
            if any(k in h for k in keywords):
                idx = i
                break
        if idx is None:
            idx = POSITIONAL_DEFAULTS.get(field)
        mapping[field] = idx
    return mapping


def parse_csv(raw, delim):
    text = raw.decode("utf-8-sig", errors="replace")
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    rows = list(reader)
    if not rows:
        raise ValueError("Empty file")
    return rows[0], rows[1:]


def _company_id(db, name, region, source):
    """Find or create a company; auto-group duplicate Investor names."""
    if not name or not name.strip():
        return None
    existing = db.execute(
        "SELECT id FROM companies WHERE LOWER(name) = LOWER(?)", (name.strip(),)
    ).fetchone()
    if existing:
        cid = existing["id"]
        db.execute(
            "UPDATE companies SET region = COALESCE(?, region), updated_at = datetime('now') "
            "WHERE id = ?",
            (region, cid),
        )
        return cid
    cur = db.execute(
        "INSERT INTO companies (name, region, source) VALUES (?, ?, ?)",
        (name.strip(), region, source),
    )
    return cur.lastrowid


def _lead_exists(db, cid, region, source_label):
    """True when a lead already exists for this company+region+source (idempotency)."""
    return db.execute(
        "SELECT id FROM leads WHERE company_id = ? AND region IS ? AND source IS ?",
        (cid, region, source_label),
    ).fetchone() is not None


def import_lead_csv(raw, source_label="", lead_source="imported"):
    """Import a dealer-layout CSV.

    Returns a dict with counts and any row-level errors.
    Creates/updates companies, locations, contacts, and one lead per row.
    """
    encoding = detect_encoding(raw)
    data = raw.decode(encoding)
    header_line = data.splitlines()[0]
    delim = detect_delimiter(header_line)
    reader = csv.reader(io.StringIO(data), delimiter=delim)
    rows = list(reader)
    if not rows:
        raise ValueError("Empty file")
    header, body = rows[0], rows[1:]

    mapping = map_columns(header)
    db = get_db()

    stats = {
        "rows": len(body),
        "companies_created": 0,
        "locations_created": 0,
        "contacts_created": 0,
        "leads_created": 0,
        "errors": [],
    }

    def cell(row, field):
        idx = mapping.get(field)
        if idx is None or idx >= len(row):
            return ""
        return (row[idx] or "").strip()

    seen_companies = {}
    for i, row in enumerate(body, start=2):
        try:
            company_name = cell(row, "company")
            region = cell(row, "region")
            city = cell(row, "city")
            address = cell(row, "address")
            plz = cell(row, "plz")
            contact_raw = cell(row, "contact")
            c_name, c_email, c_phone = parse_contact_cell(contact_raw)

            if not company_name:
                stats["errors"].append(f"Row {i}: no Investor (Group) name, skipped.")
                continue

            key = company_name.lower()
            if key in seen_companies:
                cid = seen_companies[key]
            else:
                cid = _company_id(db, company_name, region, source_label)
                if cid is None:
                    stats["errors"].append(f"Row {i}: could not create company, skipped.")
                    continue
                seen_companies[key] = cid
                stats["companies_created"] += 1

            if address or city or plz or region:
                dup_loc = db.execute(
                    "SELECT id FROM locations WHERE company_id = ? AND address IS ? AND plz IS ?",
                    (cid, address or None, plz or None),
                ).fetchone()
                if dup_loc is None:
                    db.execute(
                        "INSERT INTO locations (company_id, address, city, plz, phone) "
                        "VALUES (?, ?, ?, ?, ?)",
                        (cid, address, city, plz, c_phone or None),
                    )
                    stats["locations_created"] += 1

            if c_name or c_email or c_phone:
                dup_contact = db.execute(
                    "SELECT id FROM contacts WHERE company_id = ? AND email IS ?",
                    (cid, c_email or None),
                ).fetchone()
                if dup_contact is None:
                    db.execute(
                        "INSERT INTO contacts (company_id, name, email, phone) VALUES (?, ?, ?, ?)",
                        (cid, c_name or None, c_email or None, c_phone or None),
                    )
                    stats["contacts_created"] += 1

            if not _lead_exists(db, cid, region, lead_source or source_label or None):
                cur = db.execute(
                    "INSERT INTO leads (company_id, source, region, status) VALUES (?, ?, ?, 'new')",
                    (cid, lead_source or source_label or None, region),
                )
                stats["leads_created"] += 1
            else:
                stats["errors"].append(
                    f"Row {i}: lead already exists for {company_name} in this source, skipped."
                )
        except Exception as e:  # noqa: BLE001 - keep importing the rest
            stats["errors"].append(f"Row {i}: {e}")

    db.commit()
    return stats