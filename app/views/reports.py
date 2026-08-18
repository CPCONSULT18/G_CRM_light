import csv
import io

from flask import Response, render_template

from ..auth import visibility_where
from ..db import get_db
from . import reports_bp


@reports_bp.route("/reports")
def reports_page():
    db = get_db()
    cond, params = visibility_where("l")
    scope = f" AND {cond}" if cond else ""
    scope_lead = f" WHERE {cond}" if cond else ""

    today = db.execute("SELECT date('now') d").fetchone()["d"]

    today_stats = db.execute(
        """
        SELECT COUNT(*) AS calls,
               SUM(CASE WHEN outcome='appointment_booked' THEN 1 ELSE 0 END) AS appts,
               SUM(CASE WHEN outcome='not_interested' THEN 1 ELSE 0 END) AS not_int,
               SUM(CASE WHEN outcome='callback' THEN 1 ELSE 0 END) AS callbacks,
               SUM(CASE WHEN outcome='won' THEN 1 ELSE 0 END) AS won
        FROM activities a JOIN leads l ON l.id = a.lead_id
        WHERE a.type='call' AND date(a.occurred_at) = ?
        """
        + scope,
        [today] + params,
    ).fetchone()

    by_day = db.execute(
        """
        SELECT date(a.occurred_at) AS day, a.type,
               COUNT(*) AS n,
               SUM(CASE WHEN a.outcome='appointment_booked' THEN 1 ELSE 0 END) AS appts
        FROM activities a JOIN leads l ON l.id = a.lead_id
        """
        + scope_lead
        + """
        GROUP BY day, a.type
        ORDER BY day DESC
        LIMIT 30
        """,
        params,
    ).fetchall()

    by_region = db.execute(
        """
        SELECT COALESCE(l.region, '') AS region,
               COUNT(a.id) AS calls,
               SUM(CASE WHEN a.outcome='appointment_booked' THEN 1 ELSE 0 END) AS appts,
               SUM(CASE WHEN a.outcome='not_interested' THEN 1 ELSE 0 END) AS not_int
        FROM activities a
        JOIN leads l ON l.id = a.lead_id
        WHERE a.type = 'call'
        """
        + scope
        + """
        GROUP BY region
        ORDER BY calls DESC
        """,
        params,
    ).fetchall()

    pipeline = db.execute(
        "SELECT status, COUNT(*) AS n FROM leads l" + scope_lead + " GROUP BY status ORDER BY n DESC",
        params,
    ).fetchall()

    callbacks_due = db.execute(
        """
        SELECT a.id, a.due_date, c.name AS company_name, l.id AS lead_id
        FROM activities a
        JOIN leads l ON l.id = a.lead_id
        JOIN companies c ON c.id = l.company_id
        WHERE a.status='open' AND a.due_date IS NOT NULL
        """
        + scope
        + """
        ORDER BY a.due_date
        """,
        params,
    ).fetchall()

    return render_template(
        "reports.html",
        today=today,
        today_stats=today_stats,
        by_day=by_day,
        by_region=by_region,
        pipeline=pipeline,
        callbacks_due=callbacks_due,
    )


@reports_bp.route("/reports/export/today")
def export_today():
    db = get_db()
    cond, params = visibility_where("l")
    scope = f" AND {cond}" if cond else ""
    rows = db.execute(
        """
        SELECT date(a.occurred_at) AS day, a.outcome, a.type, a.notes,
               c.name AS company_name, l.region
        FROM activities a
        JOIN leads l ON l.id = a.lead_id
        JOIN companies c ON c.id = l.company_id
        WHERE date(a.occurred_at) = date('now')
        """
        + scope
        + """
        ORDER BY a.occurred_at
        """,
        params,
    ).fetchall()

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow(["date", "type", "outcome", "company", "region", "notes"])
    for r in rows:
        writer.writerow(
            [r["day"], r["type"], r["outcome"], r["company_name"], r["region"], r["notes"]]
        )

    return Response(
        "\ufeff" + buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=today_outcomes.csv"},
    )