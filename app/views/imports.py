import csv
import io

from flask import flash, redirect, render_template, request, url_for

from ..db import get_db
from ..importer import detect_delimiter, import_lead_csv, map_columns, parse_contact_cell
from ..matcher import run_match_all
from . import import_bp


@import_bp.route("/import")
def import_page():
    return render_template("import.html")


@import_bp.route("/import/blocklist", methods=["GET", "POST"])
def import_blocklist():
    db = get_db()
    if request.method == "GET":
        return redirect(url_for("imports.import_page"))
    if request.method == "POST":
        f = request.files.get("file")
        if f and f.filename:
            raw = f.read()
            text = raw.decode("utf-8-sig", errors="replace")
            header_line = text.splitlines()[0]
            delim = detect_delimiter(header_line)
            reader = csv.reader(io.StringIO(text), delimiter=delim)
            rows = list(reader)
            header, body = rows[0], rows[1:]

            added = 0
            for row in body:
                # Flexible: name/email/phone/domain by keyword, else positional fallback.
                rec = {}
                lowered = [h.strip().lower() for h in header]
                for field, keywords in [
                    ("email", ["email", "mail"]),
                    ("phone", ["phone", "tel", "telefon"]),
                    ("name", ["name"]),
                    ("domain", ["domain", "web"]),
                ]:
                    idx = next((i for i, h in enumerate(lowered) if any(k in h for k in keywords)), None)
                    rec[field] = (row[idx] or "").strip() if idx is not None and idx < len(row) else ""
                if not any(rec.values()):
                    continue
                db.execute(
                    "INSERT INTO contacted (name, email, phone, domain, source) "
                    "VALUES (?, ?, ?, ?, 'blocklist_import')",
                    (rec["name"] or None, rec["email"] or None, rec["phone"] or None, rec["domain"] or None),
                )
                added += 1
            db.commit()
            flash(f"Imported {added} blocklist rows.")
            return redirect(url_for("imports.import_page"))
        flash("No file uploaded.")
    return redirect(url_for("imports.import_page"))


@import_bp.route("/import/leads", methods=["GET", "POST"])
def import_leads():
    db = get_db()
    if request.method == "GET":
        return redirect(url_for("imports.import_page"))
    if request.method == "POST":
        f = request.files.get("file")
        source_label = request.form.get("source_label", "").strip()
        run_match = request.form.get("run_match") == "on"
        if f and f.filename:
            raw = f.read()
            stats = import_lead_csv(
                raw,
                source_label=source_label or f.filename,
                lead_source=source_label or "imported",
            )
            match_summary = None
            if run_match:
                match_summary = run_match_all()
            return render_template(
                "import_result.html", stats=stats, match_summary=match_summary
            )
        flash("No file uploaded.")
    return redirect(url_for("imports.import_page"))


@import_bp.route("/import/preview", methods=["POST"])
def preview_leads():
    f = request.files.get("file")
    if not f:
        return "No file", 400
    raw = f.read()
    text = raw.decode("utf-8-sig", errors="replace")
    header_line = text.splitlines()[0]
    delim = detect_delimiter(header_line)
    reader = csv.reader(io.StringIO(text), delimiter=delim)
    rows = list(reader)
    header = rows[0]
    mapping = map_columns(header)

    preview_rows = []
    for row in rows[1:6]:
        def cell(idx):
            return (row[idx] or "").strip() if idx is not None and idx < len(row) else ""
        contact_raw = cell(mapping.get("contact"))
        name, email, phone = parse_contact_cell(contact_raw)
        preview_rows.append(
            {
                "region": cell(mapping.get("region")),
                "city": cell(mapping.get("city")),
                "company": cell(mapping.get("company")),
                "address": cell(mapping.get("address")),
                "plz": cell(mapping.get("plz")),
                "contact_raw": contact_raw,
                "contact_name": name,
                "contact_email": email,
                "contact_phone": phone,
            }
        )

    return render_template(
        "import_preview.html",
        header=header,
        mapping=mapping,
        preview_rows=preview_rows,
        total=len(rows) - 1,
    )


@import_bp.route("/matches")
def match_review():
    db = get_db()
    matches = db.execute(
        """
        SELECT m.id, m.field, m.confidence, m.created_at,
               l.id AS lead_id, c.name AS company_name,
               ct.name AS contacted_name, ct.email AS contacted_email, ct.phone AS contacted_phone
        FROM matches m
        JOIN leads l ON l.id = m.lead_id
        JOIN companies c ON c.id = l.company_id
        JOIN contacted ct ON ct.id = m.contacted_id
        ORDER BY
            CASE m.confidence WHEN 'hard' THEN 1 WHEN 'probable' THEN 2 ELSE 3 END,
            c.name
        """
    ).fetchall()
    return render_template("match_review.html", matches=matches)


@import_bp.route("/matches/recount", methods=["POST"])
def recount_matches():
    summary = run_match_all()
    flash(
        f"Matched {summary['matched']} signals across {summary['leads_scanned']} leads "
        f"(hard {summary['by_confidence']['hard']}, "
        f"probable {summary['by_confidence']['probable']}, "
        f"soft {summary['by_confidence']['soft']})."
    )
    return redirect(url_for("imports.match_review"))