"""Authentication: user model, login manager, and login rate limiting.

Lockout follows MAPTOOL3's cadence discipline (sequential requests, ~4s spacing
~= 15 requests/min): a sliding-window limiter keyed by email+IP, then a hard
lock on the user row when the window budget is exceeded.
"""

import click
import threading
import time
from collections import deque

from flask import current_app
from flask_login import LoginManager, UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .db import get_db, get_setting

login_manager = LoginManager()


class User(UserMixin):
    def __init__(self, row):
        self.id = row["id"]
        self.email = row["email"]
        self.display_name = row["display_name"] or row["email"]
        self.password_hash = row["password_hash"]
        self.role = row["role"] or "user"
        self._active = bool(row["is_active"])

    @property
    def is_active(self):
        return self._active

    @property
    def is_admin(self):
        return self.role == "admin"


class LoginLimiter:
    """Sliding-window rate limiter for login attempts (Maptool cadence)."""

    def __init__(self):
        self._hits = {}
        self._lock = threading.Lock()

    def _key(self, email, ip):
        return f"{email.strip().lower()}|{ip}"

    def allow(self, email, ip, max_attempts, window_seconds):
        """Return (allowed, retry_after_seconds)."""
        key = self._key(email, ip)
        now = time.time()
        with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and bucket[0] <= now - window_seconds:
                bucket.popleft()
            if len(bucket) >= max_attempts:
                retry = window_seconds - (now - bucket[0])
                return False, max(1, int(retry))
            bucket.append(now)
            return True, 0

    def clear(self, email, ip):
        with self._lock:
            self._hits.pop(self._key(email, ip), None)


limiter = LoginLimiter()


@login_manager.user_loader
def load_user(user_id):
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if row is None:
        return None
    return User(row)


def find_user_by_email(email):
    db = get_db()
    row = db.execute("SELECT * FROM users WHERE LOWER(email) = LOWER(?)", (email,)).fetchone()
    return User(row) if row else None


def create_user(email, display_name, password, role="user", is_active=1):
    """Create a user. Returns (user, error)."""
    if not email or "@" not in email:
        return None, "Valid email required."
    if not password or len(password) < 8:
        return None, "Password must be at least 8 characters."
    if role not in ("admin", "user"):
        role = "user"
    db = get_db()
    if db.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?)", (email,)).fetchone():
        return None, "A user with that email already exists."
    cur = db.execute(
        "INSERT INTO users (email, display_name, password_hash, role, is_active) "
        "VALUES (?, ?, ?, ?, ?)",
        (email.strip(), display_name or email.split("@")[0], generate_password_hash(password), role, int(is_active)),
    )
    db.commit()
    row = db.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone()
    return User(row), None


def verify_login(email, password, ip):
    """Verify credentials with cadence-based lockout.

    Returns (user, error_or_None, retry_after).
    """
    user = find_user_by_email(email)
    max_attempts = int(get_setting("login_max_attempts", "15") or 15)
    window = int(get_setting("login_window_seconds", "60") or 60)
    lock_seconds = int(get_setting("login_lock_seconds", "900") or 900)
    db = get_db()

    # Hard lock from a previous overflow.
    if user is not None and user.is_active is False:
        return None, "This account is disabled.", 0
    if user is not None:
        row = db.execute("SELECT locked_until FROM users WHERE id = ?", (user.id,)).fetchone()
        locked_until = row["locked_until"]
        if locked_until:
            if time.time() < float(locked_until):
                retry = int(float(locked_until) - time.time()) + 1
                return None, "Too many failed attempts. Try again later.", retry
            db.execute("UPDATE users SET locked_until = NULL, failed_attempts = 0 WHERE id = ?", (user.id,))
            db.commit()

    allowed, retry = limiter.allow(email, ip, max_attempts, window)
    if not allowed:
        # Persist the lock so it survives a restart and applies to the account.
        if user is not None:
            db.execute(
                "UPDATE users SET locked_until = ?, failed_attempts = ? WHERE id = ?",
                (str(time.time() + lock_seconds), max_attempts, user.id),
            )
            db.commit()
        return None, "Too many attempts. Account temporarily locked.", retry

    if user is None or not check_password_hash(user.password_hash, password):
        if user is not None:
            db.execute(
                "UPDATE users SET failed_attempts = failed_attempts + 1 WHERE id = ?",
                (user.id,),
            )
            db.commit()
        return None, "Invalid email or password.", 0

    # Success: clear the window + counters.
    limiter.clear(email, ip)
    db.execute(
        "UPDATE users SET failed_attempts = 0, locked_until = NULL, last_login = datetime('now') WHERE id = ?",
        (user.id,),
    )
    db.commit()
    return user, None, 0


def set_password(user_id, new_password):
    if not new_password or len(new_password) < 8:
        return "Password must be at least 8 characters."
    db = get_db()
    db.execute(
        "UPDATE users SET password_hash = ?, updated_at = datetime('now') WHERE id = ?",
        (generate_password_hash(new_password), user_id),
    )
    db.commit()
    return None


def admin_count():
    db = get_db()
    return db.execute("SELECT COUNT(*) c FROM users WHERE role = 'admin'").fetchone()["c"]


def visibility_where(alias="l"):
    """Return (sql_condition, params) scoping rows to the current user.

    Admins see everything; normal users see only leads where `responsible`
    equals their display name.
    """
    from flask_login import current_user

    if not current_user.is_authenticated or current_user.is_admin:
        return "", []
    return f"LOWER({alias}.responsible) = LOWER(?)", [current_user.display_name]


@click.command("create-user")
@click.option("--email", required=True)
@click.option("--name", default=None, help="Display name shown in the app.")
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
@click.option("--role", default="user", type=click.Choice(["admin", "user"]))
@click.option("--active/--inactive", default=True)
def create_user_command(email, name, password, role, active):
    """Create an app user (admin by passing --role admin)."""
    user, error = create_user(
        email, name, password, role=role, is_active=int(active)
    )
    if error:
        raise click.ClickException(error)
    click.echo(f"Created {role} user: {user.email} ({user.display_name})")


def init_app(app):
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please sign in to continue."
    login_manager.login_message_category = "message"
    app.cli.add_command(create_user_command)
