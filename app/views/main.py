from flask import render_template

from ..db import get_db
from . import main_bp


@main_bp.route("/")
def index():
    db = get_db()

    total_leads = db.execute("SELECT COUNT(*) c FROM leads").fetchone()["c"]
    open_callbacks = db.execute(
        "SELECT COUNT(*) c FROM activities WHERE status='open' AND due_date IS NOT NULL"
    ).fetchone()["c"]
    appointments = db.execute(
        "SELECT COUNT(*) c FROM activities WHERE outcome='appointment_booked'"
    ).fetchone()["c"]
    hard_matches = db.execute(
        "SELECT COUNT(DISTINCT lead_id) c FROM matches WHERE confidence='hard'"
    ).fetchone()["c"]
    total_companies = db.execute("SELECT COUNT(*) c FROM companies").fetchone()["c"]

    recent = db.execute(
        """
        SELECT a.*, c.name AS company_name, l.status AS lead_status
        FROM activities a
        JOIN leads l ON l.id = a.lead_id
        JOIN companies c ON c.id = l.company_id
        ORDER BY a.occurred_at DESC
        LIMIT 10
        """
    ).fetchall()

    return render_template(
        "index.html",
        total_leads=total_leads,
        open_callbacks=open_callbacks,
        appointments=appointments,
        hard_matches=hard_matches,
        total_companies=total_companies,
        recent=recent,
    )