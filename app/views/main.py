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


@main_bp.route("/today")
def today():
    db = get_db()
    today = db.execute("SELECT date('now') d").fetchone()["d"]

    # Open callbacks due on or before today.
    callbacks = db.execute(
        """
        SELECT a.id AS activity_id, a.due_date, a.notes AS cb_note,
               l.id AS lead_id, l.region, c.name AS company_name,
               (SELECT COUNT(*) FROM contacts k WHERE k.company_id = c.id) AS n_contacts,
               (SELECT COUNT(*) FROM locations o WHERE o.company_id = c.id) AS n_locations,
               (SELECT GROUP_CONCAT(DISTINCT m.confidence) FROM matches m WHERE m.lead_id = l.id) AS match_confs
        FROM activities a
        JOIN leads l ON l.id = a.lead_id
        JOIN companies c ON c.id = l.company_id
        WHERE a.status = 'open' AND a.due_date IS NOT NULL AND a.due_date <= ?
        ORDER BY a.due_date
        """,
        (today,),
    ).fetchall()

    # Fresh leads (status new/called/no_answer/voicemail) that are NOT hard-matched,
    # oldest first, grouped by region priority.
    fresh = db.execute(
        """
        SELECT l.id AS lead_id, l.region, l.status, l.created_at,
               c.name AS company_name,
               (SELECT COUNT(*) FROM contacts k WHERE k.company_id = c.id) AS n_contacts,
               (SELECT COUNT(*) FROM locations o WHERE o.company_id = c.id) AS n_locations,
               (SELECT GROUP_CONCAT(DISTINCT m.confidence) FROM matches m WHERE m.lead_id = l.id) AS match_confs
        FROM leads l
        JOIN companies c ON c.id = l.company_id
        WHERE l.status IN ('new', 'called', 'no_answer', 'voicemail')
          AND NOT EXISTS (
              SELECT 1 FROM matches m
              WHERE m.lead_id = l.id AND m.confidence = 'hard'
          )
        ORDER BY l.region, l.created_at
        """
    ).fetchall()

    return render_template("today.html", callbacks=callbacks, fresh=fresh, today=today)