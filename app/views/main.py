from flask import render_template

from ..auth import visibility_where
from ..db import get_db
from . import main_bp


def _scope(alias="l"):
    """Returns (cond_sql, params) scoping to current user's visible leads.

    cond_sql is a bare condition (no WHERE/AND prefix) or empty string.
    """
    return visibility_where(alias)


@main_bp.route("/")
def index():
    db = get_db()

    leads_cond, leads_params = _scope("l")
    where = f" WHERE {leads_cond}" if leads_cond else ""
    and_ = f" AND {leads_cond}" if leads_cond else ""

    total_leads = db.execute(
        "SELECT COUNT(*) c FROM leads l" + where, leads_params
    ).fetchone()["c"]
    open_callbacks = db.execute(
        "SELECT COUNT(*) c FROM activities a JOIN leads l ON l.id = a.lead_id"
        + where
        + " AND a.status='open' AND a.due_date IS NOT NULL",
        leads_params,
    ).fetchone()["c"]
    appointments = db.execute(
        "SELECT COUNT(*) c FROM activities a JOIN leads l ON l.id = a.lead_id"
        + where
        + " AND a.outcome='appointment_booked'",
        leads_params,
    ).fetchone()["c"]
    hard_matches = db.execute(
        "SELECT COUNT(DISTINCT m.lead_id) c FROM matches m JOIN leads l ON l.id = m.lead_id"
        + where
        + " AND m.confidence='hard'",
        leads_params,
    ).fetchone()["c"]
    total_companies = db.execute(
        "SELECT COUNT(DISTINCT l.company_id) c FROM leads l" + where,
        leads_params,
    ).fetchone()["c"]

    recent = db.execute(
        """
        SELECT a.*, c.name AS company_name, l.status AS lead_status
        FROM activities a
        JOIN leads l ON l.id = a.lead_id
        JOIN companies c ON c.id = l.company_id
        """
        + where
        + """
        ORDER BY a.occurred_at DESC
        LIMIT 10
        """,
        leads_params,
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
    leads_cond, leads_params = _scope("l")
    and_ = f" AND {leads_cond}" if leads_cond else ""

    # Open callbacks due on or before today.
    callbacks = db.execute(
        """
        SELECT a.id AS activity_id, a.due_date, a.notes AS cb_note,
               l.id AS lead_id, l.region, c.name AS company_name,
               (SELECT COUNT(*) FROM contacts k WHERE k.company_id = c.id) AS n_contacts,
               (SELECT COUNT(*) FROM locations o WHERE o.company_id = c.id) AS n_locations,
               (SELECT GROUP_CONCAT(DISTINCT m.confidence) FROM matches m WHERE m.lead_id = l.id) AS match_confs,
               EXISTS(SELECT 1 FROM activities x WHERE x.lead_id = l.id AND x.outcome = 'replied') AS replied
        FROM activities a
        JOIN leads l ON l.id = a.lead_id
        JOIN companies c ON c.id = l.company_id
        WHERE a.status = 'open' AND a.due_date IS NOT NULL AND a.due_date <= ?
        """
        + and_
        + """
        ORDER BY a.due_date
        """,
        [today] + leads_params,
    ).fetchall()

    # Fresh leads (status new/called/no_answer/voicemail) that are NOT hard-matched,
    # oldest first, grouped by region priority.
    fresh = db.execute(
        """
        SELECT l.id AS lead_id, l.region, l.status, l.created_at,
               c.name AS company_name,
               (SELECT COUNT(*) FROM contacts k WHERE k.company_id = c.id) AS n_contacts,
               (SELECT COUNT(*) FROM locations o WHERE o.company_id = c.id) AS n_locations,
               (SELECT GROUP_CONCAT(DISTINCT m.confidence) FROM matches m WHERE m.lead_id = l.id) AS match_confs,
               EXISTS(SELECT 1 FROM activities a WHERE a.lead_id = l.id AND a.outcome = 'replied') AS replied
        FROM leads l
        JOIN companies c ON c.id = l.company_id
        WHERE l.status IN ('new', 'called', 'no_answer', 'voicemail')
        """
        + and_
        + """
          AND NOT EXISTS (
              SELECT 1 FROM matches m
              WHERE m.lead_id = l.id AND m.confidence = 'hard'
          )
          AND NOT EXISTS (
              SELECT 1 FROM activities a
              WHERE a.lead_id = l.id AND a.outcome = 'replied'
          )
        ORDER BY l.region, l.created_at
        """,
        leads_params,
    ).fetchall()

    return render_template("today.html", callbacks=callbacks, fresh=fresh, today=today)