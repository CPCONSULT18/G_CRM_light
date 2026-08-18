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
# Keyword order = priority: "investor" must win over "group" (BWBA files have a
# separate Group column), and "responsible" is only present in the rich export.
HEADER_MAP = [
    ("responsible", ["responsible", "verantwortlich"]),
    ("region", ["metro", "area", "state", "bundesland"]),
    ("city", ["city", "ort"]),
    ("company", ["investor", "group", "firma", "company", "firm"]),
    ("address", ["dealer location street", "street", "strasse", "straße", "address"]),
    ("plz", ["zip", "plz", "postal", "postleitzahl"]),
    ("contact", ["contact at dealer", "contact", "kontakt"]),
    ("blocked", ["blocked by signed dealer", "blocked"]),
]

POSITIONAL_DEFAULTS = {
    "region": 0,
    "city": 1,
    "company": 5,
    "address": 6,
    "plz": 7,
    "contact": 10,
}

# Acquisition summary fields from the rich SharePoint export -> leads columns.
# Exact header text (lowercased, stripped) -> internal field name.
ACQUISITION_SUMMARY = {
    "last status": "last_status",
    "entrypoint": "entrypoint",
    "status": "gad_status",
    "sales & service?": "sales_service",
    "acquisition status": "acquisition_status",
    "acquisition progress": "acquisition_progress",
}

# Step-date columns: headers starting with "NN. ..." or "LOI signed ...".
STEP_HEADER_RE = re.compile(r"^(\d{1,2})\.\s+(.*)$", re.IGNORECASE)
LOI_HEADER_RE = re.compile(r"^loi\b", re.IGNORECASE)

# Canonical acquisition pipeline steps in display order (for the edit UI).
PIPELINE_STEPS = [
    ("01", "01. First contact"),
    ("02", "02. NDA Signed"),
    ("03", "03. Formal GAD Intro (online) w/ Dealer Pitch Deck"),
    ("LOI", "LOI signed (not needed anymore)"),
    ("04", "04. Send Dealer Information Pack"),
    ("05", "05. Visit (Acquisition Agent)"),
    ("06", "06. Dealer visit report (internal) - prepared by Acquisition agent"),
    ("07", "07. High Profile: Raunheim visit & Demo Car Pick Up"),
    ("08", "08. Dealer BP template sent"),
    ("09", "09. Dealer BP received"),
    ("10", "10. Consors Quick Check Date"),
    ("11", "11. Dealer BP score card population by internal experts (based on Dealer BP form)"),
    ("12", "12. Dealer application Form approval by Business Function"),
    ("13", "13. BP certificate  signed by MD"),
    ("14", "14. Approval visit on site (internal task)"),
    ("15", "15. Send contract details questionnaire documetation to dealer"),
    ("16", "16. received contract details questionnaire to dealer"),
    ("17", "17. Sent for signature to dealer"),
    ("18", "18. Signed by Dealer"),
    ("19", "19. Sent to GAD for signature"),
    ("20", "20. Signed by GAD"),
    ("21", "21. Signed contract distributed"),
]


def scan_acquisition_columns(header):
    """Return (summary_map, steps) from the rich export header.

    summary_map: {field: col_index} for the 6 acquisition summary fields.
    steps: list of (step_key, step_label, col_index) in header order.
    """
    summary_map = {}
    steps = []
    for i, raw in enumerate(header):
        h = (raw or "").strip().lower()
        if not h:
            continue
        if h in ACQUISITION_SUMMARY:
            summary_map[ACQUISITION_SUMMARY[h]] = i
        m = STEP_HEADER_RE.match(h)
        if m:
            steps.append((m.group(1).zfill(2), (raw or "").strip(), i))
        elif LOI_HEADER_RE.match(h):
            steps.append(("LOI", (raw or "").strip(), i))
    return summary_map, steps


def normalize_date(value):
    """Best-effort date normalization to ISO (YYYY-MM-DD), else raw string.

    Supports M/D/YYYY (US, as in the rich export), D.M.YYYY (German), and
    ISO. Unparseable values are returned unchanged.
    """
    value = (value or "").strip()
    if not value:
        return None
    m = re.match(r"^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$", value)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    m = re.match(r"^(\d{1,2})[/](\d{1,2})[/](\d{4})$", value)
    if m:
        mon, day, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{year:04d}-{mon:02d}-{day:02d}"
    m = re.match(r"^(\d{1,2})[.](\d{1,2})[.](\d{4})$", value)
    if m:
        day, mon, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{year:04d}-{mon:02d}-{day:02d}"
    return value


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
    """Return {field: col_index} by matching header keywords, else position.

    Keywords are checked in priority order (HEADER_MAP order), and for each
    keyword all columns are scanned so e.g. "investor" wins over "group".
    """
    mapping = {}
    lowered = [h.strip().lower() for h in header]
    for field, keywords in HEADER_MAP:
        idx = None
        for kw in keywords:
            for i, h in enumerate(lowered):
                if kw in h:
                    idx = i
                    break
            if idx is not None:
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


def _replace_pipeline_events(db, lead_id, steps, row):
    """Replace a lead's pipeline step dates (idempotent re-import)."""
    db.execute("DELETE FROM pipeline_events WHERE lead_id = ?", (lead_id,))
    for step_key, step_label, col in steps:
        step_date = None
        if col is not None and col < len(row):
            step_date = normalize_date(row[col])
        db.execute(
            "INSERT INTO pipeline_events (lead_id, step_key, step_label, step_date) "
            "VALUES (?, ?, ?, ?)",
            (lead_id, step_key, step_label, step_date),
        )


def import_lead_csv(raw, source_label="", lead_source="imported"):
    """Import a dealer-layout CSV.

    Returns a dict with counts and any row-level errors.
    Creates/updates companies, locations, contacts, and one lead per row.
    Rich exports also store acquisition summary fields and 22 pipeline
    step-dates; re-importing the same file updates (not duplicates) leads.
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
    summary_map, steps = scan_acquisition_columns(header)
    db = get_db()

    stats = {
        "rows": len(body),
        "companies_created": 0,
        "locations_created": 0,
        "contacts_created": 0,
        "leads_created": 0,
        "leads_updated": 0,
        "pipeline_leads": 0,
        "errors": [],
    }

    def cell(row, field):
        idx = mapping.get(field)
        if idx is None or idx >= len(row):
            return ""
        return (row[idx] or "").strip()

    def acq_cell(row, field):
        idx = summary_map.get(field)
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
            responsible = cell(row, "responsible")
            if responsible:
                responsible = re.sub(r"\s+", " ", responsible).strip().title()
            contact_raw = cell(row, "contact")
            c_name, c_email, c_phone = parse_contact_cell(contact_raw)
            blocked_raw = cell(row, "blocked")
            blocked = bool(blocked_raw and blocked_raw.lower().startswith("block"))

            acquisition = {
                "last_status": acq_cell(row, "last_status") or None,
                "entrypoint": acq_cell(row, "entrypoint") or None,
                "gad_status": acq_cell(row, "gad_status") or None,
                "sales_service": acq_cell(row, "sales_service") or None,
                "acquisition_status": acq_cell(row, "acquisition_status") or None,
                "acquisition_progress": acq_cell(row, "acquisition_progress") or None,
            }

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

            existing = db.execute(
                "SELECT id FROM leads WHERE company_id = ? AND region IS ? AND source IS ?",
                (cid, region, lead_source or source_label or None),
            ).fetchone()
            if existing:
                lead_id = existing["id"]
                db.execute(
                    "UPDATE leads SET responsible = ?, status = ?, "
                    "last_status = ?, entrypoint = ?, gad_status = ?, sales_service = ?, "
                    "acquisition_status = ?, acquisition_progress = ?, "
                    "updated_at = datetime('now') WHERE id = ?",
                    (
                        responsible or None,
                        "blocked" if blocked else "new",
                        acquisition["last_status"],
                        acquisition["entrypoint"],
                        acquisition["gad_status"],
                        acquisition["sales_service"],
                        acquisition["acquisition_status"],
                        acquisition["acquisition_progress"],
                        lead_id,
                    ),
                )
                stats["leads_updated"] += 1
            else:
                cur = db.execute(
                    "INSERT INTO leads (company_id, source, region, responsible, status, "
                    "last_status, entrypoint, gad_status, sales_service, "
                    "acquisition_status, acquisition_progress) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        cid,
                        lead_source or source_label or None,
                        region,
                        responsible or None,
                        "blocked" if blocked else "new",
                        acquisition["last_status"],
                        acquisition["entrypoint"],
                        acquisition["gad_status"],
                        acquisition["sales_service"],
                        acquisition["acquisition_status"],
                        acquisition["acquisition_progress"],
                    ),
                )
                lead_id = cur.lastrowid
                stats["leads_created"] += 1

            if steps:
                _replace_pipeline_events(db, lead_id, steps, row)
                stats["pipeline_leads"] += 1
        except Exception as e:  # noqa: BLE001 - keep importing the rest
            stats["errors"].append(f"Row {i}: {e}")

    db.commit()
    return stats