import os

from flask import Flask

from . import db


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=False)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("LEADFLOW_SECRET", "dev-local-only"),
        MAX_CONTENT_LENGTH=50 * 1024 * 1024,
    )

    if test_config:
        app.config.update(test_config)

    db.init_app(app)

    from .views import main_bp, leads_bp, import_bp, map_bp, reports_bp, settings_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(import_bp)
    app.register_blueprint(map_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)

    return app