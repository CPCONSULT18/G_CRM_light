"""Saved-report engine: config-driven query builder over whitelisted sources.

Every identifier (source, dimension, metric, time field, filter field) is
validated against SOURCES before being interpolated into SQL. All values are
parameterized. Lead-linked sources always apply the current user's visibility
scope (see auth.visibility_where).
"""

from types import SimpleNamespace

from .auth import visibility_where
from .db import get_db

# source -> {from_sql, dims, metrics, time_fields, default_metric}
SOURCES = {
    "leads": {
        "from": "leads l JOIN companies c ON c.id = l.company_id",
        "dims": {
            "region": "COALESCE(l.region, '(empty)')",
            "status": "COALESCE(l.status, '(empty)')",
            "responsible": "COALESCE(l.responsible, '(empty)')",
            "source": "COALESCE(l.source, '(empty)')",
            "acquisition_status": "COALESCE(l.acquisition_status, '(empty)')",
            "entrypoint": "COALESCE(l.entrypoint, '(empty)')",
            "gad_status": "COALESCE(l.gad_status, '(empty)')",
            "month": "strftime('%Y-%m', l.created_at)",
            "company": "COALESCE(c.name, '(empty)')",
        },
        "metrics": {
            "count": "COUNT(*)",
            "count_companies": "COUNT(DISTINCT l.company_id)",
            "avg_qual": "AVG(l.qual_score)",
        },
        "time_fields": {
            "created_at": "l.created_at",
            "updated_at": "l.updated_at",
        },
        "default_metric": "count",
    },
    "activities": {
        "from": (
            "activities a JOIN leads l ON l.id = a.lead_id "
            "JOIN companies c ON c.id = l.company_id"
        ),
        "dims": {
            "outcome": "COALESCE(a.outcome, '(none)')",
            "type": "COALESCE(a.type, '(none)')",
            "day": "date(a.occurred_at)",
            "month": "strftime('%Y-%m', a.occurred_at)",
            "region": "COALESCE(l.region, '(empty)')",
            "responsible": "COALESCE(l.responsible, '(empty)')",
            "status": "COALESCE(l.status, '(empty)')",
            "company": "COALESCE(c.name, '(empty)')",
        },
        "metrics": {
            "count": "COUNT(*)",
            "count_leads": "COUNT(DISTINCT l.id)",
            "count_appointments": (
                "SUM(CASE WHEN a.outcome = 'appointment_booked' THEN 1 ELSE 0 END)"
            ),
            "count_won": "SUM(CASE WHEN a.outcome = 'won' THEN 1 ELSE 0 END)",
        },
        "time_fields": {
            "occurred_at": "a.occurred_at",
            "due_date": "a.due_date",
        },
        "default_metric": "count",
    },
    "pipeline": {
        "from": (
            "pipeline_events pe JOIN leads l ON l.id = pe.lead_id "
            "JOIN companies c ON c.id = l.company_id"
        ),
        "dims": {
            "step": "pe.step_label",
            "month": "strftime('%Y-%m', pe.step_date)",
            "region": "COALESCE(l.region, '(empty)')",
            "responsible": "COALESCE(l.responsible, '(empty)')",
            "acquisition_status": "COALESCE(l.acquisition_status, '(empty)')",
        },
        "metrics": {
            "count_leads": "COUNT(DISTINCT l.id)",
        },
        "time_fields": {
            "step_date": "pe.step_date",
            "created_at": "l.created_at",
        },
        "default_metric": "count_leads",
    },
}

TIME_PRESETS = {
    "": "no time filter",
    "7d": "last 7 days",
    "30d": "last 30 days",
    "90d": "last 90 days",
    "this_month": "this month",
    "custom": "custom range",
}

CHART_TYPES = ("pie", "bar", "number")


def _filter_sql(cond, op, value):
    if op == "contains":
        return f"{cond} LIKE ?", [f"%{value}%"]
    if op == "eq":
        return f"{cond} = ?", [value]
    if op == "ne":
        return f"{cond} != ?", [value]
    raise ValueError(f"Unknown filter op: {op}")


def _time_clause(source, config):
    """Return (sql_conditions, params) for the configured time filter."""
    time_field = config.get("time_field") or ""
    if time_field not in source["time_fields"]:
        return [], []
    expr = source["time_fields"][time_field]
    preset = config.get("time_preset") or ""
    from_ = (config.get("time_from") or "").strip()
    to = (config.get("time_to") or "").strip()

    conds, params = [], []
    if preset in ("7d", "30d", "90d"):
        days = int(preset[:-1])
        conds.append(f"date({expr}) >= date('now', '-{days} days')")
    elif preset == "this_month":
        conds.append(f"strftime('%Y-%m', {expr}) = strftime('%Y-%m', 'now')")
    elif preset == "custom" or (from_ or to):
        if from_:
            conds.append(f"date({expr}) >= date(?)")
            params.append(from_)
        if to:
            conds.append(f"date({expr}) <= date(?)")
            params.append(to)
    return conds, params


def run_report(config):
    """Execute a report config dict; returns result data for rendering.

    Result keys: labels, values, rows (label/value pairs), total, metric,
    source, dim, chart, is_number.
    """
    db = get_db()
    source = SOURCES.get(config.get("source"))
    if source is None:
        raise ValueError("Unknown source")

    metric = config.get("metric") or source["default_metric"]
    if metric not in source["metrics"]:
        raise ValueError(f"Unknown metric: {metric}")
    metric_sql = source["metrics"][metric]

    dim = config.get("dimension") or ""
    if dim and dim not in source["dims"]:
        raise ValueError(f"Unknown dimension: {dim}")
    dim_sql = source["dims"][dim] if dim else None

    where, params = [], []
    vis_cond, vis_params = visibility_where("l")
    if vis_cond:
        where.append(vis_cond)
        params += vis_params

    for f in config.get("filters") or []:
        field = f.get("field")
        op = f.get("op", "eq")
        value = (f.get("value") or "").strip()
        if not field or not value:
            continue
        if field in source["dims"]:
            cond = source["dims"][field]
        elif field in source["metrics"]:
            cond = source["metrics"][field]
        else:
            continue
        sql, fparams = _filter_sql(cond, op, value)
        where.append(sql)
        params += fparams

    tconds, tparams = _time_clause(source, config)
    where += tconds
    params += tparams

    if dim_sql:
        select = f"SELECT {dim_sql} AS _label, {metric_sql} AS _v FROM {source['from']}"
        if where:
            select += " WHERE " + " AND ".join(where)
        select += f" GROUP BY {dim_sql}"
        try:
            limit = max(1, min(int(config.get("limit") or 50), 200))
        except (TypeError, ValueError):
            limit = 50
        select += " ORDER BY _v DESC, _label ASC LIMIT ?"
        params = params + [limit]
    else:
        select = f"SELECT {metric_sql} AS _v FROM {source['from']}"
        if where:
            select += " WHERE " + " AND ".join(where)

    rows = db.execute(select, params).fetchall()

    if dim_sql:
        labels = [r["_label"] for r in rows]
        values = [r["_v"] or 0 for r in rows]
    else:
        labels = []
        values = [rows[0]["_v"] or 0] if rows else [0]

    chart = config.get("chart") or ("bar" if dim_sql else "number")
    if chart not in CHART_TYPES:
        chart = "bar" if dim_sql else "number"

    total = sum(values)
    return SimpleNamespace(
        labels=labels,
        values=values,
        rows=[SimpleNamespace(label=l, value=v) for l, v in zip(labels, values)],
        total=total,
        metric=metric,
        source=config.get("source"),
        dim=dim,
        chart=chart,
        is_number=chart == "number",
        is_pie=chart == "pie",
    )