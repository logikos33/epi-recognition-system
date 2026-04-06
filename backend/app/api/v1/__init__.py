"""Register all v1 blueprints — failures are isolated per module."""
import logging

logger = logging.getLogger(__name__)


def register_all_blueprints(app) -> None:
    """Register each blueprint independently — one failure doesn't block others."""
    blueprints = [
        ("backend.app.api.v1.health.routes", "health_bp"),
        ("backend.app.api.v1.auth.routes", "auth_bp"),
        ("backend.app.api.v1.videos.routes", "videos_bp"),
        ("backend.app.api.v1.annotations.routes", "annotations_bp"),
        ("backend.app.api.v1.training.routes", "training_bp"),
        ("backend.app.api.v1.cameras.routes", "cameras_bp"),
    ]

    loaded = []
    degraded = []

    for module_path, bp_name in blueprints:
        try:
            import importlib
            module = importlib.import_module(module_path)
            bp = getattr(module, bp_name)
            app.register_blueprint(bp)
            loaded.append(bp_name)
        except Exception as e:
            logger.warning("[DEGRADED] Blueprint %s failed to load: %s", bp_name, e)
            degraded.append(bp_name)

    logger.info("Blueprints loaded: %s", loaded)
    if degraded:
        logger.warning("Blueprints degraded: %s", degraded)
