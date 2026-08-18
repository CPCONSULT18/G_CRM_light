from flask import Response, redirect, render_template, request, url_for

from ..db import get_db
from . import leads_bp


def _lead_query(filters):
    """Shared lead query builder; returns (sql, params) for list + export."""
    region = filters.get("region", "")
    status = filters.get("status", "")
    match_filter = filters.get("match", "")

    sql = """
        SELECT l.id, l.source, l.region, l.responsible, l.qual_score, l.status, l.created_at,
               c.name AS company_name, c.id AS company_id,
               (SELECT COUNT(*) FROM contacts k WHERE k.company_id = c.id) AS n_contacts,
               (SELECT COUNT(*) FROM locations o WHERE o.company_id = c.id) AS n_locations,
               (SELECT GROUP_CONCAT(DISTINCT m.confidence) FROM matches m WHERE m.lead_id = l.id) AS match_confs,
               EXISTS(SELECT 1 FROM activities a WHERE a.lead_id = l.id AND a.outcome = 'replied') AS replied
        FROM leads l
        JOIN companies c ON c.id = l.company_id
    """
    conds, params = [], []

    if region:
        conds.append("(l.region LIKE ? OR c.region LIKE ?)")
        params += [f"%{region}%", f"%{region}%"]
    if status:
        conds.append("l.status = ?")
        params.append(status)
    if match_filter in ("hard", "probable", "soft", "clear"):
        if match_filter == "clear":
            conds.append("NOT EXISTS (SELECT 1 FROM matches m WHERE m.lead_id = l.id)")
        else:
            conds.append(
                "EXISTS (SELECT 1 FROM matches m WHERE m.lead_id = l.id AND m.confidence = ?)"
            )
            params.append(match_filter)
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    sql += " ORDER BY c.name, l.created_at"
    return sql, params


@leads_bp.route("/leads")
def list_leads():
    db = get_db()
    filters = {
        "region": request.args.get("region", "").strip(),
        "status": request.args.get("status", "").strip(),
        "match": request.args.get("match", "").strip(),
    }
    sql, params = _lead_query(filters)
    leads = db.execute(sql, params).fetchall()

    regions = db.execute(
        "SELECT DISTINCT region FROM leads WHERE region IS NOT NULL AND region != '' ORDER BY region"
    ).fetchall()

    return render_template(
        "leads.html",
        leads=leads,
        regions=[r["region"] for r in regions],
        filters=filters,
    )


@leads_bp.route("/leads/<int:lead_id>")
def lead_detail(lead_id):
    db = get_db()
    lead = db.execute(
        """
        SELECT l.*, c.name AS company_name, c.region AS company_region
        FROM leads l JOIN companies c ON c.id = l.company_id
        WHERE l.id = ?
        """,
        (lead_id,),
    ).fetchone()
    if lead is None:
        return "Lead not found", 404

    contacts = db.execute(
        "SELECT * FROM contacts WHERE company_id = ?", (lead["company_id"],)
    ).fetchall()
    locations = db.execute(
        "SELECT * FROM locations WHERE company_id = ?", (lead["company_id"],)
    ).fetchall()
    activities = db.execute(
        "SELECT * FROM activities WHERE lead_id = ? ORDER BY occurred_at DESC, id DESC",
        (lead_id,),
    ).fetchall()
    matches = db.execute(
        """
        SELECT m.*, ct.name AS c_name, ct.email AS c_email, ct.phone AS c_phone
        FROM matches m JOIN contacted ct ON ct.id = m.contacted_id
        WHERE m.lead_id = ? ORDER BY
            CASE m.confidence WHEN 'hard' THEN 1 WHEN 'probable' THEN 2 ELSE 3 END
        """,
        (lead_id,),
    ).fetchall()

    return render_template(
        "lead_detail.html",
        lead=lead,
        contacts=contacts,
        locations=locations,
        activities=activities,
        matches=matches,
    )


@leads_bp.route("/leads/<int:lead_id>/outcome", methods=["POST"])
def log_outcome(lead_id):
    outcome = request.form.get("outcome", "")
    due_date = request.form.get("due_date", "") or None
    notes = request.form.get("notes", "").strip() or None

    db = get_db()
    db.execute(
        "INSERT INTO activities (lead_id, type, outcome, notes, due_date, status) "
        "VALUES (?, 'call', ?, ?, ?, ?)",
        (lead_id, outcome, notes, due_date, "open" if due_date else "done"),
    )

    # Drive lead status from outcome.
    status_map = {
        "not_interested": "not_interested",
        "callback": "callback",
        "appointment_booked": "appointment",
        "won": "won",
        "lost": "lost",
        "called": "called",
    }
    new_status = status_map.get(outcome)
    if new_status:
        db.execute(
            "UPDATE leads SET status = ?, updated_at = datetime('now') WHERE id = ?",
            (new_status, lead_id),
        )
    db.commit()
    return redirect(url_for("leads.lead_detail", lead_id=lead_id))


@leads_bp.route("/leads/export")
def export_leads():
    import csv
    import io

    db = get_db()
    filters = {
        "region": request.args.get("region", "").strip(),
        "status": request.args.get("status", "").strip(),
        "match": request.args.get("match", "").strip(),
    }
    sql, params = _lead_query(filters)
    rows = db.execute(sql, params).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(
        ["company", "region", "responsible", "status", "source", "matches", "contacts", "locations", "created"]
    )
    for r in rows:
        writer.writerow(
            [
                r["company_name"],
                r["region"] or "",
                r["responsible"] or "",
                r["status"],
                r["source"] or "",
                r["match_confs"] or "",
                r["n_contacts"],
                r["n_locations"],
                (r["created_at"] or "")[:10],
            ]
        )

    return Response(
        "\ufeff" + buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )