from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.security import check_password_hash

from ..auth import admin_count, create_user, set_password
from ..db import get_db
from . import users_bp


def _require_admin():
    if not current_user.is_authenticated or not current_user.is_admin:
        return False
    return True


@users_bp.route("/users")
@login_required
def list_users():
    if not _require_admin():
        flash("Admin access required.")
        return redirect(url_for("main.index"))
    db = get_db()
    users = db.execute(
        "SELECT id, email, display_name, role, is_active, failed_attempts, locked_until, last_login, created_at "
        "FROM users ORDER BY email"
    ).fetchall()
    return render_template("users.html", users=users)


@users_bp.route("/users/create", methods=["POST"])
@login_required
def create():
    if not _require_admin():
        flash("Admin access required.")
        return redirect(url_for("main.index"))
    email = request.form.get("email", "").strip()
    name = request.form.get("display_name", "").strip()
    password = request.form.get("password", "")
    role = request.form.get("role", "user")
    user, error = create_user(email, name, password, role=role)
    if error:
        flash(error, "error")
    else:
        flash(f"User {user.email} created.")
    return redirect(url_for("users.list_users"))


@users_bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@login_required
def toggle(user_id):
    if not _require_admin():
        flash("Admin access required.")
        return redirect(url_for("main.index"))
    db = get_db()
    row = db.execute("SELECT id, is_active FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        flash("User not found.", "error")
    else:
        db.execute(
            "UPDATE users SET is_active = ?, locked_until = NULL, updated_at = datetime('now') WHERE id = ?",
            (0 if row["is_active"] else 1, user_id),
        )
        db.commit()
        flash("User updated.")
    return redirect(url_for("users.list_users"))


@users_bp.route("/users/<int:user_id>/reset", methods=["POST"])
@login_required
def reset_password(user_id):
    if not _require_admin():
        flash("Admin access required.")
        return redirect(url_for("main.index"))
    password = request.form.get("password", "")
    error = set_password(user_id, password)
    flash(error or "Password reset.", "error" if error else "message")
    return redirect(url_for("users.list_users"))


@users_bp.route("/users/<int:user_id>/unlock", methods=["POST"])
@login_required
def unlock(user_id):
    if not _require_admin():
        flash("Admin access required.")
        return redirect(url_for("main.index"))
    db = get_db()
    db.execute(
        "UPDATE users SET locked_until = NULL, failed_attempts = 0, updated_at = datetime('now') WHERE id = ?",
        (user_id,),
    )
    db.commit()
    flash("User unlocked.")
    return redirect(url_for("users.list_users"))


@users_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    error = None
    ok = None
    if request.method == "POST":
        current_pw = request.form.get("current_password", "")
        new_pw = request.form.get("new_password", "")
        display_name = request.form.get("display_name", "").strip()

        row = db.execute(
            "SELECT password_hash FROM users WHERE id = ?", (current_user.id,)
        ).fetchone()
        if not check_password_hash(row["password_hash"], current_pw):
            error = "Current password is incorrect."
        else:
            if display_name:
                db.execute(
                    "UPDATE users SET display_name = ?, updated_at = datetime('now') WHERE id = ?",
                    (display_name, current_user.id),
                )
            if new_pw:
                error = set_password(current_user.id, new_pw)
            db.commit()
            if error is None:
                ok = "Profile updated."

    return render_template("profile.html", error=error, ok=ok, admin_total=admin_count())
