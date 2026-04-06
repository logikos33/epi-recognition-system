"""Celery factory with separate queues per module."""
import logging
import os

logger = logging.getLogger(__name__)

_celery = None


def create_celery(app=None):
    """Create Celery with separate queues — graceful if Redis unavailable."""
    global _celery
    try:
        from celery import Celery

        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        _celery = Celery(
            "epi_monitor",
            broker=redis_url,
            backend=redis_url,
        )
        _celery.conf.update(
            task_serializer="json",
            result_serializer="json",
            accept_content=["json"],
            timezone="UTC",
            task_queues={
                "videos": {"exchange": "videos"},
                "annotations": {"exchange": "annotations"},
                "training": {"exchange": "training"},
                "streaming": {"exchange": "streaming"},
                "inference": {"exchange": "inference"},
            },
            task_default_queue="default",
            worker_prefetch_multiplier=1,
        )
        logger.info("Celery initialized (broker=%s)", redis_url)
        return _celery
    except Exception as e:
        logger.warning("Celery init failed (queue features degraded): %s", e)
        return None


def get_celery():
    return _celery
