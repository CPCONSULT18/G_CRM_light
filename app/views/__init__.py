from flask import Blueprint

main_bp = Blueprint("main", __name__)
leads_bp = Blueprint("leads", __name__)
import_bp = Blueprint("imports", __name__)
map_bp = Blueprint("map", __name__)
reports_bp = Blueprint("reports", __name__)
settings_bp = Blueprint("settings", __name__)

from . import main, leads, imports, map_view, reports, settings, gmail  # noqa: E402,F401