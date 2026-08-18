from flask import flash, redirect, render_template, request, url_for

from .. import gmail_service
from ..db import get_db, get_setting, set_setting
from . import settings_bp


@settings_bp.route("/settings", methods=["GET", "POST"])
def settings_page():
    if request.method == "POST":
        set_setting("country_code", request.form.get("country_code", "49").strip())
        set_setting("ors_api_key", request.form.get("ors_api_key", "").strip())
        set_setting("gmail_client_id", request.form.get("gmail_client_id", "").strip())
        set_setting("gmail_client_secret", request.form.get("gmail_client_secret", "").strip())
        flash("Settings saved.")
        return redirect(url_for("settings.settings_page"))

    return render_template(
        "settings.html",
        country_code=get_setting("country_code", "49"),
        ors_api_key=get_setting("ors_api_key", ""),
        gmail_client_id=get_setting("gmail_client_id", ""),
        gmail_client_secret=get_setting("gmail_client_secret", ""),
        gmail_user=get_setting("gmail_user", ""),
        gmail_connected=gmail_service.load_credentials() is not None,
    )


@settings_bp.route("/settings/data", methods=["POST"])
def data_actions():
    action = request.form.get("action")
    db = get_db()
    if action == "wipe":
        for table in (
            "matches",
            "activities",
            "opportunities",
            "leads",
            "contacts",
            "locations",
            "companies",
        ):
            db.execute(f"DELETE FROM {table}")
        db.commit()
        flash("All CRM data wiped.")
    return redirect(url_for("settings.settings_page"))