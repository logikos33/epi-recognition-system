"""WSGI entry point for production (gunicorn).

Startup design:
- create_app() runs synchronously (fast — just blueprint registration)
- Migrations run in a background thread after app starts
- /health responds immediately, before migrations complete
"""
import logging
import threading

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

from backend.app import create_app

app = create_app()


def _run_migrations_background():
    """Run migrations in background — failures don't prevent startup."""
    try:
        from backend.app.infrastructure.database.connection import db_pool
        from backend.app.infrastructure.database.migrations import run_migrations
        with app.app_context():
            results = run_migrations(db_pool)
            if results.get("failed"):
                logger.warning("[STARTUP] Migrations degraded: %s", results["failed"])
            else:
                logger.info("[STARTUP] Migrations OK (%d applied, %d skipped)",
                            len(results.get("ok", [])), len(results.get("skipped", [])))
    except Exception as e:
        logger.warning("[STARTUP] Migration thread error (degraded): %s", e)


# Start migrations in background — doesn't block gunicorn startup
_migration_thread = threading.Thread(
    target=_run_migrations_background,
    daemon=True,
    name="migrations",
)
_migration_thread.start()


# Health check — responds immediately even during migration
@app.get("/health")
def health():
    from flask import jsonify
    migration_running = _migration_thread.is_alive()
    return jsonify({
        "status": "ok",
        "version": "2.0.0",
        "migrations": "running" if migration_running else "done",
    })
