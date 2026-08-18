from flask import flash, redirect, render_template, request, url_for

from .. import gmail_service
from ..db import get_db, get_setting, set_setting
from . import settings_bp

REDIRECT_PATH = "/gmail/callback"


def _redirect_uri():
    return request.host_url.rstrip("/") + REDIRECT_PATH


@settings_bp.route("/gmail/connect")
def gmail_connect():
    cid, _ = gmail_service._client()
    if not cid:
        flash("Save Gmail Client ID and Client Secret in Settings first.")
        return redirect(url_for("settings.settings_page"))
    url = gmail_service.build_auth_url(_redirect_uri())
    return redirect(url)


@settings_bp.route(REDIRECT_PATH)
def gmail_callback():
    code = request.args.get("code")
    error = request.args.get("error")
    if error or not code:
        flash(f"Gmail authorization failed: {error or 'no code'}")
        return redirect(url_for("settings.settings_page"))
    try:
        email = gmail_service.exchange_code(code, _redirect_uri())
    except Exception as e:  # noqa: BLE001
        flash(f"Gmail token exchange failed: {e}")
        return redirect(url_for("settings.settings_page"))
    set_setting("gmail_user", email)
    flash(f"Gmail connected as {email}.")
    return redirect(url_for("settings.settings_page"))


@settings_bp.route("/gmail/disconnect", methods=["POST"])
def gmail_disconnect():
    gmail_service.revoke_token()
    flash("Gmail disconnected.")
    return redirect(url_for("settings.settings_page"))


@settings_bp.route("/gmail/poll", methods=["POST"])
def gmail_poll():
    created, seen, status = gmail_service.poll_replies()
    if status == "ok":
        flash(f"Gmail poll done: {created} new reply(ies) logged, {seen} seen.")
    else:
        flash(f"Gmail poll: {status}")
    return redirect(url_for("settings.settings_page"))
