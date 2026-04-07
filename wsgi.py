"""WSGI entry point for production (gunicorn + eventlet)."""
import eventlet
eventlet.monkey_patch()  # MUST be first — required for flask-socketio eventlet mode

import logging
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

from backend.app import create_app
from backend.app.extensions import get_socketio

app = create_app()


def _run_migrations():
    try:
        from backend.app.infrastructure.database.connection import db_pool
        from backend.app.infrastructure.database.migrations import run_migrations
        with app.app_context():
            results = run_migrations(db_pool)
            logger.info("[MIGRATIONS] %s", results)
    except Exception as e:
        logger.warning("[MIGRATIONS] Failed (degraded): %s", e)


threading.Thread(target=_run_migrations, daemon=True, name="migrations").start()


@app.get("/health")
def health():
    from flask import jsonify
    return jsonify({"status": "ok", "version": "2.0.0"})
