"""Health check functions."""
import logging
import os

logger = logging.getLogger(__name__)


def check_database() -> dict:
    try:
        from backend.app.infrastructure.database.connection import db_pool
        if not db_pool.is_available:
            return {"status": "unavailable"}
        with db_pool.get_cursor() as cur:
            cur.execute("SELECT 1")
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}


def check_redis() -> dict:
    try:
        import redis
        r = redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"), socket_timeout=2)
        r.ping()
        return {"status": "ok"}
    except Exception:
        return {"status": "unavailable"}


def check_yolo() -> dict:
    model_path = os.environ.get("YOLO_MODEL_PATH", "models/yolov8n.pt")
    if not os.path.exists(model_path):
        return {"status": "unavailable", "reason": "model file not found"}
    try:
        import ultralytics
        return {"status": "ok", "version": ultralytics.__version__}
    except ImportError:
        return {"status": "unavailable", "reason": "ultralytics not installed"}
