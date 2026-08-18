from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_user, logout_user

from ..auth import verify_login
from . import auth_bp


def _client_ip():
    if request.headers.get("X-Forwarded-For"):
        return request.headers.get("X-Forwarded-For").split(",")[0].strip()
    return request.remote_addr or ""


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    error = None
    retry_after = 0
    if request.method == "POST":
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        user, error, retry_after = verify_login(email, password, _client_ip())
        if user is not None:
            login_user(user)
            next_url = request.args.get("next") or url_for("main.index")
            if not next_url.startswith("/") or next_url.startswith("//"):
                next_url = url_for("main.index")
            return redirect(next_url)
        if retry_after:
            flash(f"Too many attempts. Try again in ~{retry_after}s.", "error")
        else:
            flash("Invalid email or password.", "error")

    return render_template("login.html", error=error, retry_after=retry_after)


@auth_bp.route("/logout", methods=["POST"])
def logout():
    logout_user()
    flash("Signed out.")
    return redirect(url_for("auth.login"))
