"""EPI Monitor — Flask Application Factory."""
import logging
import os

from flask import Flask
from flask_cors import CORS

logger = logging.getLogger(__name__)


def create_app(config_name: str | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration — fallback to production for unknown envs (e.g. "staging")
    from backend.app.config import config_by_name, ProductionConfig
    cfg_name = config_name or os.environ.get("FLASK_ENV", "production")
    app.config.from_object(config_by_name.get(cfg_name, ProductionConfig))

    # CORS — NEVER bare CORS(app), always use whitelist
    origins = os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(",")
    CORS(app, origins=[o.strip() for o in origins if o.strip()], supports_credentials=True)

    # Initialize extensions
    _init_extensions(app)

    # Register blueprints
    _register_blueprints(app)

    # Register error handlers
    from backend.app.core.middleware import register_error_handlers
    register_error_handlers(app)

    logger.info("EPI Monitor application created [env=%s]", cfg_name)
    return app


def _init_extensions(app: Flask) -> None:
    """Initialize Flask extensions — each with graceful degradation."""
    # Database pool
    from backend.app.infrastructure.database.connection import db_pool
    try:
        db_pool.init_app(app)
        logger.info("Database pool initialized")
    except Exception as e:
        logger.warning("Database pool init failed (degraded): %s", e)

    # SocketIO — init with Redis message_queue for multi-worker support
    _init_socketio(app)


def _init_socketio(app: Flask) -> None:
    """Initialize Flask-SocketIO with Redis message_queue (graceful degradation)."""
    from backend.app.extensions import set_socketio
    try:
        from flask_socketio import SocketIO
        redis_url = app.config.get("REDIS_URL", "")
        cors_origins = app.config.get("CORS_ORIGINS", "*").split(",")

        socketio = SocketIO(
            app,
            cors_allowed_origins=[o.strip() for o in cors_origins if o.strip()],
            async_mode="eventlet",
            message_queue=redis_url if redis_url else None,
            logger=False,
            engineio_logger=False,
        )

        set_socketio(socketio)

        # Start Redis→SocketIO bridge for camera detections
        try:
            from backend.app.api.v1.cameras.socket_events import init_socket_events
            init_socket_events(socketio, redis_url)
            logger.info("SocketIO initialized (Redis bridge active)")
        except Exception as e:
            logger.warning("SocketIO Redis bridge degraded: %s", e)
            logger.info("SocketIO initialized (no Redis bridge)")

    except ImportError:
        logger.warning("flask-socketio not installed — WebSocket features degraded")
    except Exception as e:
        logger.warning("SocketIO init failed (degraded): %s", e)


def _register_blueprints(app: Flask) -> None:
    """Register all blueprints — failures are isolated."""
    from backend.app.api.v1 import register_all_blueprints
    register_all_blueprints(app)
