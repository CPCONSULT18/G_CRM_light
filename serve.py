"""Production entrypoint: serve the app on 127.0.0.1 via Waitress.

Run behind the Caddy reverse proxy (see Caddyfile), which terminates TLS and
forwards requests to http://127.0.0.1:5000.
"""

from app import create_app
from app.db import init_db

if __name__ == "__main__":
    init_db()
    app = create_app()
    from waitress import serve

    serve(app, host="127.0.0.1", port=5000, threads=8)
