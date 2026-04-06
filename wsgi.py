"""WSGI entry point for production (gunicorn)."""
import logging
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

from backend.app import create_app
from backend.app.infrastructure.database.connection import db_pool
from backend.app.infrastructure.database.migrations import run_migrations

app = create_app()

# Run migrations on startup (graceful — failures don't prevent boot)
with app.app_context():
    results = run_migrations(db_pool)
    if results["failed"]:
        import logging
        logging.getLogger(__name__).warning(
            "Some migrations failed — affected features degraded: %s", results["failed"]
        )
    else:
        import logging
        logging.getLogger(__name__).info("Migrations OK")

# Legacy /health route for Railway health checks
@app.get("/health")
def legacy_health():
    from flask import jsonify
    return jsonify({"status": "ok", "version": "2.0.0"})
