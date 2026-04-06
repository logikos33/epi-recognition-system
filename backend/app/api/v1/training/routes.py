"""Training blueprint."""
import logging

from flask import Blueprint, g, request

from backend.app.core.auth import require_auth
from backend.app.core.responses import created, error, not_found, success

logger = logging.getLogger(__name__)

training_bp = Blueprint("training", __name__, url_prefix="/api/v1/training")


@training_bp.get("/jobs")
@require_auth
def list_jobs():
    try:
        from backend.app.api.v1.training.service import TrainingService
        jobs = TrainingService.list_jobs(g.user_id)
        return success(jobs)
    except Exception as e:
        logger.error("List training jobs error: %s", e)
        return error("Failed to list training jobs", 500)


@training_bp.post("/jobs")
@require_auth
def create_job():
    data = request.get_json(silent=True) or {}
    epochs = data.get("epochs", 100)
    batch_size = data.get("batch_size", 16)
    try:
        from backend.app.api.v1.training.service import TrainingService
        job = TrainingService.create_job(g.user_id, epochs, batch_size)
        return created(job, "Training job created")
    except Exception as e:
        logger.error("Create training job error: %s", e)
        return error("Failed to create training job", 500)


@training_bp.get("/jobs/<job_id>")
@require_auth
def get_job(job_id: str):
    try:
        from backend.app.api.v1.training.service import TrainingService
        job = TrainingService.get_job(g.user_id, job_id)
        if not job:
            return not_found("Training job")
        return success(job)
    except Exception as e:
        return error("Failed to get training job", 500)
