import json
import time

from flask import Response, flash, redirect, render_template, request, url_for

from ..db import get_db, get_setting
from ..normalize import norm_phone
from . import map_bp

NOMINATIM = "https://nominatim.openstreetmap.org/search"
ORS_ENDPOINT = "https://api.openrouteservice.org/v2/isochrones/driving-car"
GEO_DELAY = 1.1
ORS_BATCH_SIZE = 5
ORS_BATCH_PAUSE = 15


@map_bp.route("/map")
def map_page():
    db = get_db()
    locations = db.execute(
        """
        SELECT o.id, o.address, o.city, o.plz, o.lat, o.lng, o.geocode_status,
               c.name AS company_name
        FROM locations o JOIN companies c ON c.id = o.company_id
        WHERE o.lat IS NOT NULL AND o.lng IS NOT NULL
        ORDER BY c.name
        """
    ).fetchall()
    pending_geocode = db.execute(
        """
        SELECT COUNT(*) c FROM locations
        WHERE (lat IS NULL OR lng IS NULL) AND (address IS NOT NULL AND address != '')
        """
    ).fetchone()["c"]
    return render_template(
        "map.html",
        locations=locations,
        has_ors_key=bool(get_setting("ors_api_key")),
        pending_geocode=pending_geocode,
    )


@map_bp.route("/map/locations")
def map_locations():
    db = get_db()
    locations = db.execute(
        """
        SELECT o.id, o.address, o.city, o.plz, o.lat, o.lng, o.geocode_status, o.iso_json,
               c.name AS company_name
        FROM locations o JOIN companies c ON c.id = o.company_id
        WHERE o.lat IS NOT NULL AND o.lng IS NOT NULL
        """
    ).fetchall()
    payload = []
    for loc in locations:
        payload.append(
            {
                "id": loc["id"],
                "name": loc["company_name"],
                "address": loc["address"],
                "city": loc["city"],
                "plz": loc["plz"],
                "lat": loc["lat"],
                "lng": loc["lng"],
                "geocode_status": loc["geocode_status"],
                "iso_json": loc["iso_json"],
            }
        )
    return Response(json.dumps(payload), mimetype="application/json")


@map_bp.route("/map/geocode", methods=["POST"])
def geocode():
    import requests

    db = get_db()
    pending = db.execute(
        """
        SELECT id, address, city, plz FROM locations
        WHERE (lat IS NULL OR lng IS NULL) AND (address IS NOT NULL AND address != '')
        """
    ).fetchall()

    done, failed = 0, 0
    for loc in pending:
        q = build_query(loc)
        lat, lng = query_nominatim(q)
        if lat is None:
            fallback = f"{loc['plz']}, Deutschland" if loc["plz"] else None
            if fallback:
                lat, lng = query_nominatim(fallback)
        if lat is None:
            db.execute(
                "UPDATE locations SET geocode_status='failed' WHERE id = ?", (loc["id"],)
            )
            failed += 1
        else:
            db.execute(
                "UPDATE locations SET lat=?, lng=?, geocode_status='ok' WHERE id = ?",
                (lat, lng, loc["id"]),
            )
            done += 1
        time.sleep(GEO_DELAY)

    db.commit()
    flash(f"Geocoded {done} location(s), {failed} failed.")
    return redirect(url_for("map.map_page"))


def build_query(loc):
    if loc["address"]:
        return f"{loc['address']}, {loc['plz']} {loc['city']}, Deutschland"
    if loc["plz"] and loc["city"]:
        return f"{loc['plz']} {loc['city']}, Deutschland"
    return None


def query_nominatim(q):
    import requests

    headers = {"User-Agent": "LeadFlowCRM/1.0 (local-crm)"}
    for attempt in range(1, 4):
        try:
            r = requests.get(
                NOMINATIM,
                params={"q": q, "format": "json", "limit": 1, "countrycodes": "de"},
                headers=headers,
                timeout=15,
            )
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", "5")) + 1
                time.sleep(wait)
                continue
            r.raise_for_status()
            results = r.json()
            if not results:
                return None, None
            return float(results[0]["lat"]), float(results[0]["lon"])
        except requests.RequestException:
            time.sleep(2 * attempt)
    return None, None


@map_bp.route("/map/isochrones", methods=["POST"])
def isochrones():
    import requests

    db = get_db()
    key = get_setting("ors_api_key")
    if not key:
        flash("No ORS API key configured. Paste one in Settings first.")
        return redirect(url_for("map.map_page"))

    locations = db.execute(
        """
        SELECT id, lat, lng, iso_json FROM locations
        WHERE lat IS NOT NULL AND lng IS NOT NULL
        """
    ).fetchall()

    for sec, label in ((1800, "30-min"), (1200, "20-min")):
        todo = []
        for loc in locations:
            cached = json.loads(loc["iso_json"]) if loc["iso_json"] else {}
            if cached.get(label):
                continue  # cached, skip
            todo.append(loc)
        for i in range(0, len(todo), ORS_BATCH_SIZE):
            batch = todo[i : i + ORS_BATCH_SIZE]
            for loc in batch:
                feature = fetch_iso(loc["lat"], loc["lng"], sec, key)
                cached = json.loads(loc["iso_json"]) if loc["iso_json"] else {}
                if feature is not None:
                    cached[label] = feature
                db.execute(
                    "UPDATE locations SET iso_json = ? WHERE id = ?",
                    (json.dumps(cached), loc["id"]),
                )
            db.commit()
            if i + ORS_BATCH_SIZE < len(todo):
                time.sleep(ORS_BATCH_PAUSE)

    flash("Isochrones fetched (rate-limited).")
    return redirect(url_for("map.map_page"))


def fetch_iso(lat, lng, range_sec, key):
    import requests

    try:
        r = requests.post(
            ORS_ENDPOINT,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            json={"locations": [[lng, lat]], "range": [range_sec], "range_type": "time", "units": "m"},
            timeout=60,
        )
        if r.status_code == 429:
            wait = float(r.headers.get("Retry-After", "5")) + 1
            time.sleep(wait)
            return None
        r.raise_for_status()
        return r.json()
    except requests.RequestException:
        return None