"""WSGI entry point — diagnostic minimal version."""
import logging
import os

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

try:
    from backend.app import create_app
    app = create_app()
    logger.info("[STARTUP] Full app loaded successfully")
except Exception as e:
    logger.error("[STARTUP] Full app failed to load: %s", e, exc_info=True)
    # Fallback: minimal Flask app so Railway health check passes
    from flask import Flask, jsonify
    app = Flask(__name__)
    _startup_error = str(e)

    @app.get("/health")
    def health_fallback():
        return jsonify({"status": "degraded", "error": _startup_error}), 200

    @app.get("/")
    def root():
        return jsonify({"status": "degraded", "error": _startup_error}), 200
else:
    import threading

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
