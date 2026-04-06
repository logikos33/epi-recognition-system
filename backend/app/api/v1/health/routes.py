"""Health check blueprint — granular per-service checks."""
import logging
import os

from flask import Blueprint, jsonify

from backend.app.infrastructure.database.connection import db_pool

logger = logging.getLogger(__name__)

health_bp = Blueprint("health", __name__, url_prefix="/api/v1/health")


@health_bp.get("/")
def health_root():
    """Top-level health check."""
    return jsonify({
        "status": "ok",
        "service": "epi-monitor",
        "version": os.environ.get("APP_VERSION", "2.0.0"),
    })


@health_bp.get("/db")
def health_db():
    """Database health check."""
    if not db_pool.is_available:
        return jsonify({"status": "unavailable", "service": "database"}), 503
    try:
        with db_pool.get_cursor() as cur:
            cur.execute("SELECT 1")
        return jsonify({"status": "ok", "service": "database"})
    except Exception as e:
        logger.warning("DB health check failed: %s", e)
        return jsonify({"status": "error", "service": "database", "detail": "connection failed"}), 503


@health_bp.get("/redis")
def health_redis():
    """Redis health check."""
    try:
        import redis
        r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"), socket_timeout=2)
        r.ping()
        return jsonify({"status": "ok", "service": "redis"})
    except Exception:
        return jsonify({"status": "unavailable", "service": "redis"}), 503


@health_bp.get("/yolo")
def health_yolo():
    """YOLO model health check."""
    model_path = os.environ.get("YOLO_MODEL_PATH", "models/yolov8n.pt")
    if not os.path.exists(model_path):
        return jsonify({"status": "unavailable", "service": "yolo", "path": model_path}), 503
    try:
        import ultralytics
        return jsonify({"status": "ok", "service": "yolo", "version": ultralytics.__version__})
    except ImportError:
        return jsonify({"status": "unavailable", "service": "yolo", "detail": "ultralytics not installed"}), 503


# Legacy health endpoint for backward compatibility
@health_bp.get("")
def health_legacy():
    return health_root()
