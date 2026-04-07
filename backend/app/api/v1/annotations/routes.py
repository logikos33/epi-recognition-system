"""Annotations blueprint."""
import logging

from flask import Blueprint, g, request

from backend.app.core.auth import require_auth
from backend.app.core.responses import created, error, not_found, success

logger = logging.getLogger(__name__)

annotations_bp = Blueprint("annotations", __name__, url_prefix="/api/v1/annotations")


@annotations_bp.get("/frames")
@require_auth
def list_frames():
    try:
        from backend.app.api.v1.annotations.service import AnnotationService
        video_id = request.args.get("video_id")
        frames = AnnotationService.list_frames(g.user_id, video_id)
        return success(frames)
    except Exception as e:
        logger.error("List frames error: %s", e)
        return error("Failed to list frames", 500)


@annotations_bp.get("/frames/<frame_id>")
@require_auth
def get_frame(frame_id: str):
    try:
        from backend.app.api.v1.annotations.service import AnnotationService
        frame = AnnotationService.get_frame(g.user_id, frame_id)
        if not frame:
            return not_found("Frame")
        return success(frame)
    except Exception as e:
        return error("Failed to get frame", 500)


@annotations_bp.post("/frames/<frame_id>/labels")
@require_auth
def save_labels(frame_id: str):
    data = request.get_json(silent=True) or {}
    labels = data.get("labels", [])
    try:
        from backend.app.api.v1.annotations.service import AnnotationService
        AnnotationService.save_labels(g.user_id, frame_id, labels)
        return success(message="Labels saved")
    except Exception as e:
        logger.error("Save labels error: %s", e)
        return error("Failed to save labels", 500)


@annotations_bp.get("/classes")
@require_auth
def list_classes():
    try:
        from backend.app.api.v1.annotations.service import AnnotationService
        classes = AnnotationService.list_classes(g.user_id)
        return success(classes)
    except Exception as e:
        return error("Failed to list classes", 500)


@annotations_bp.post("/classes")
@require_auth
def create_class():
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()
    color = data.get("color", "#00ff00")
    if not name:
        return error("Class name required", 422)
    try:
        from backend.app.api.v1.annotations.service import AnnotationService
        cls = AnnotationService.create_class(g.user_id, name, color)
        return created(cls, "Class created")
    except Exception as e:
        logger.error("Create class error: %s", e)
        return error("Failed to create class", 500)


@annotations_bp.post("/dataset/build")
@require_auth
def build_dataset():
    try:
        from backend.app.api.v1.annotations.tasks import dispatch_build_dataset_version
        result = dispatch_build_dataset_version(g.user_id)
        return success(result, "Dataset versioning started")
    except Exception as e:
        logger.error("Build dataset error: %s", e)
        return error(str(e), 500)


@annotations_bp.get("/dataset/versions")
@require_auth
def list_dataset_versions():
    try:
        from backend.app.infrastructure.database.connection import db_pool
        with db_pool.get_cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'dataset_versions'
                )
            """)
            if not cur.fetchone()["exists"]:
                return success([])
            cur.execute(
                "SELECT id, version, metadata, r2_prefix, created_at FROM dataset_versions WHERE user_id = %s ORDER BY created_at DESC",
                (g.user_id,),
            )
            versions = [dict(r) for r in cur.fetchall()]
            return success(versions)
    except Exception as e:
        logger.error("List dataset versions error: %s", e)
        return error("Failed to list dataset versions", 500)
