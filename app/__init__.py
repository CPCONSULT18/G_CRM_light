import os

from flask import Flask, redirect, request, url_for
from flask_login import current_user
from flask_wtf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

from . import db
from .auth import init_app as init_auth

csrf = CSRFProtect()

PUBLIC_ENDPOINTS = {"auth.login", "auth.logout"}


def _secret_key(data_dir):
    env = os.environ.get("LEADFLOW_SECRET")
    if env:
        return env
    key_file = os.path.join(data_dir, "secret_key")
    if os.path.exists(key_file):
        with open(key_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    key = os.urandom(32).hex()
    with open(key_file, "w", encoding="utf-8") as f:
        f.write(key)
    return key


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=False)

    data_dir = os.environ.get("LEADFLOW_DATA", os.path.join(os.path.dirname(app.root_path), "data"))
    os.makedirs(data_dir, exist_ok=True)
    os.environ.setdefault("LEADFLOW_DATA", data_dir)

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    app.config.from_mapping(
        SECRET_KEY=_secret_key(data_dir),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        # Secure cookies are only required behind the Caddy TLS proxy; the
        # plain-HTTP dev server (run.py) needs them off so login persists.
        SESSION_COOKIE_SECURE=os.environ.get("LEADFLOW_COOKIE_SECURE", "0") == "1",
        WTF_CSRF_TIME_LIMIT=None,
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    csrf.init_app(app)
    init_auth(app)

    from .views import (
        auth_bp,
        import_bp,
        leads_bp,
        main_bp,
        map_bp,
        reports_bp,
        settings_bp,
        users_bp,
    )

    app.register_blueprint(main_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(import_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)

    @app.before_request
    def require_login():
        if request.endpoint in PUBLIC_ENDPOINTS or request.endpoint == "static":
            return
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))

    return app