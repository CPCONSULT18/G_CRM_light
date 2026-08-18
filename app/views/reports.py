import csv
import io
import json

from flask import Response, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from ..auth import visibility_where
from ..db import get_db
from ..reporting import CHART_TYPES, SOURCES, TIME_PRESETS, run_report
from . import reports_bp


def _visible_report_where():
    """Scoping for saved reports: owner only, admin sees all."""
    if current_user.is_authenticated and current_user.is_admin:
        return "", []
    return "r.owner_id = ?", [current_user.id]


def _load_report(report_id):
    db = get_db()
    cond, params = _visible_report_where()
    where = "r.id = ?"
    params = [report_id] + params
    if cond:
        where += f" AND {cond}"
    return db.execute(
        f"SELECT r.* FROM reports r WHERE {where}", params
    ).fetchone()


@reports_bp.route("/reports")
@login_required
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

    my_cond, my_params = _visible_report_where()
    my_where = f" WHERE {my_cond}" if my_cond else ""
    saved = db.execute(
        "SELECT id, name, kind, updated_at FROM reports r" + my_where + " ORDER BY name",
        my_params,
    ).fetchall()

    return render_template(
        "reports.html",
        today=today,
        today_stats=today_stats,
        by_day=by_day,
        by_region=by_region,
        pipeline=pipeline,
        callbacks_due=callbacks_due,
        saved=saved,
        chart_types=CHART_TYPES,
        sources=list(SOURCES),
        time_presets=TIME_PRESETS,
    )


@reports_bp.route("/reports/new", methods=["GET", "POST"])
@login_required
def build_report():
    if request.method == "GET":
        return render_template(
            "report_build.html",
            sources=SOURCES,
            chart_types=CHART_TYPES,
            time_presets=TIME_PRESETS,
            error=None,
            config=None,
            result=None,
        )

    name = request.form.get("name", "").strip()
    if not name:
        return render_template(
            "report_build.html",
            sources=SOURCES,
            chart_types=CHART_TYPES,
            time_presets=TIME_PRESETS,
            error="A report name is required.",
            config=request.form,
            result=None,
        )

    config = {
        "source": request.form.get("source", ""),
        "dimension": request.form.get("dimension", "") or "",
        "metric": request.form.get("metric", "") or "",
        "chart": request.form.get("chart", "") or "",
        "limit": request.form.get("limit", "50") or "50",
        "time_field": request.form.get("time_field", "") or "",
        "time_preset": request.form.get("time_preset", "") or "",
        "time_from": request.form.get("time_from", "") or "",
        "time_to": request.form.get("time_to", "") or "",
        "filters": [],
    }

    # Parse filter rows: filter_field_N / filter_op_N / filter_value_N
    i = 0
    while True:
        field = request.form.get(f"filter_field_{i}", "").strip()
        op = request.form.get(f"filter_op_{i}", "eq").strip()
        value = request.form.get(f"filter_value_{i}", "").strip()
        if not field:
            break
        if value:
            config["filters"].append({"field": field, "op": op, "value": value})
        i += 1

    action = request.form.get("action", "")
    try:
        result = run_report(config)
    except ValueError as e:
        return render_template(
            "report_build.html",
            sources=SOURCES,
            chart_types=CHART_TYPES,
            time_presets=TIME_PRESETS,
            error=str(e),
            config=request.form,
            result=None,
        )

    if action == "preview":
        return render_template(
            "report_build.html",
            sources=SOURCES,
            chart_types=CHART_TYPES,
            time_presets=TIME_PRESETS,
            error=None,
            config=request.form,
            result=result,
        )

    # Save
    db = get_db()
    cur = db.execute(
        "INSERT INTO reports (owner_id, name, kind, config_json) VALUES (?, ?, 'report', ?)",
        (current_user.id, name, json.dumps(config)),
    )
    db.commit()
    flash(f"Report '{name}' saved.")
    return redirect(url_for("reports.view_report", report_id=cur.lastrowid))


@reports_bp.route("/reports/<int:report_id>")
@login_required
def view_report(report_id):
    report = _load_report(report_id)
    if report is None:
        return "Report not found", 404

    if report["kind"] == "dashboard":
        db = get_db()
        data = json.loads(report["config_json"] or "{}")
        ids = data.get("report_ids") or []
        widgets = []
        for rid in ids:
            sub = _load_report(rid)
            if sub is None or sub["kind"] != "report":
                continue
            try:
                cfg = json.loads(sub["config_json"] or "{}")
                widgets.append(
                    {"name": sub["name"], "result": run_report(cfg), "id": sub["id"]}
                )
            except ValueError:
                continue
        return render_template(
            "dashboard_view.html", report=report, widgets=widgets
        )

    try:
        config = json.loads(report["config_json"] or "{}")
        result = run_report(config)
    except (ValueError, json.JSONDecodeError) as e:
        return render_template(
            "report_view.html", report=report, error=str(e), result=None
        )
    return render_template(
        "report_view.html", report=report, result=result, error=None
    )


@reports_bp.route("/reports/<int:report_id>/delete", methods=["POST"])
@login_required
def delete_report(report_id):
    report = _load_report(report_id)
    if report is None:
        return "Report not found", 404
    db = get_db()
    db.execute("DELETE FROM reports WHERE id = ?", (report_id,))
    db.commit()
    flash(f"Report '{report['name']}' deleted.")
    return redirect(url_for("reports.reports_page"))


@reports_bp.route("/reports/dashboards/new", methods=["GET", "POST"])
@login_required
def build_dashboard():
    db = get_db()
    my_cond, my_params = _visible_report_where()
    my_where = f" WHERE {my_cond} AND r.kind = 'report'" if my_cond else " WHERE r.kind = 'report'"
    reports = db.execute(
        "SELECT id, name FROM reports r" + my_where + " ORDER BY name", my_params
    ).fetchall()

    if request.method == "GET":
        return render_template("dashboard_build.html", reports=reports)

    name = request.form.get("name", "").strip()
    if not name:
        flash("A dashboard name is required.", "error")
        return render_template("dashboard_build.html", reports=reports)

    ids = [int(x) for x in request.form.getlist("report_ids") if x.isdigit()]
    if not ids:
        flash("Select at least one report.", "error")
        return render_template("dashboard_build.html", reports=reports)

    config = json.dumps({"report_ids": ids})
    cur = db.execute(
        "INSERT INTO reports (owner_id, name, kind, config_json) VALUES (?, ?, 'dashboard', ?)",
        (current_user.id, name, config),
    )
    db.commit()
    flash(f"Dashboard '{name}' saved.")
    return redirect(url_for("reports.view_report", report_id=cur.lastrowid))


@reports_bp.route("/reports/<int:report_id>/export")
@login_required
def export_report(report_id):
    report = _load_report(report_id)
    if report is None:
        return "Report not found", 404
    if report["kind"] != "report":
        return "Only reports can be exported.", 400
    try:
        config = json.loads(report["config_json"] or "{}")
        result = run_report(config)
    except (ValueError, json.JSONDecodeError) as e:
        return f"Report error: {e}", 400

    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")
    writer.writerow([report["name"]])
    writer.writerow(["label", "value"])
    for r in result.rows:
        writer.writerow([r.label, r.value])
    writer.writerow(["TOTAL", result.total])

    safe = "".join(c for c in report["name"] if c.isalnum() or c in " _-") or "report"
    return Response(
        "\ufeff" + buf.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={safe.strip()}.csv"},
    )


@reports_bp.route("/reports/export/today")
@login_required
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