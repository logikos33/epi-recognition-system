"""Cameras blueprint."""
import logging

from flask import Blueprint, g, request

from backend.app.core.auth import require_auth
from backend.app.core.responses import created, error, not_found, success

logger = logging.getLogger(__name__)

cameras_bp = Blueprint("cameras", __name__, url_prefix="/api/v1/cameras")


@cameras_bp.get("/")
@require_auth
def list_cameras():
    try:
        from backend.app.api.v1.cameras.service import CameraService
        cameras = CameraService.list_cameras(g.user_id)
        return success(cameras)
    except Exception as e:
        logger.error("List cameras error: %s", e)
        return error("Failed to list cameras", 500)


@cameras_bp.post("/")
@require_auth
def create_camera():
    data = request.get_json(silent=True) or {}
    try:
        from backend.app.api.v1.cameras.service import CameraService
        camera = CameraService.create_camera(g.user_id, data)
        return created(camera, "Camera created")
    except Exception as e:
        logger.error("Create camera error: %s", e)
        return error(str(e), 422 if "invalid" in str(e).lower() else 500)


@cameras_bp.get("/<camera_id>")
@require_auth
def get_camera(camera_id: str):
    try:
        from backend.app.api.v1.cameras.service import CameraService
        camera = CameraService.get_camera(g.user_id, camera_id)
        if not camera:
            return not_found("Camera")
        return success(camera)
    except Exception as e:
        return error("Failed to get camera", 500)


@cameras_bp.put("/<camera_id>")
@require_auth
def update_camera(camera_id: str):
    data = request.get_json(silent=True) or {}
    try:
        from backend.app.api.v1.cameras.service import CameraService
        camera = CameraService.update_camera(g.user_id, camera_id, data)
        if not camera:
            return not_found("Camera")
        return success(camera, "Camera updated")
    except Exception as e:
        return error(str(e), 422 if "invalid" in str(e).lower() else 500)


@cameras_bp.delete("/<camera_id>")
@require_auth
def delete_camera(camera_id: str):
    try:
        from backend.app.api.v1.cameras.service import CameraService
        CameraService.delete_camera(g.user_id, camera_id)
        return success(message="Camera deleted")
    except Exception as e:
        return error("Failed to delete camera", 500)


@cameras_bp.post("/test")
@require_auth
def test_camera():
    data = request.get_json(silent=True) or {}
    rtsp_url = data.get("rtsp_url", "")
    try:
        from backend.app.api.v1.cameras.rtsp_validator import RTSPUrlValidator
        RTSPUrlValidator.validate(rtsp_url)
        return success({"valid": True, "url": rtsp_url})
    except Exception as e:
        return error(str(e), 422)


@cameras_bp.post("/<camera_id>/stream/start")
@require_auth
def start_stream(camera_id: str):
    try:
        from backend.app.api.v1.cameras.service import CameraService
        from backend.app.api.v1.cameras.tasks import start_camera_stream
        camera = CameraService.get_camera(g.user_id, camera_id)
        if not camera:
            return not_found("Camera")
        rtsp_url = camera.get("rtsp_url", "")
        if not rtsp_url:
            return error("Camera has no RTSP URL configured", 422)
        result = start_camera_stream(camera_id, rtsp_url)
        return success(result, "Stream started")
    except Exception as e:
        logger.error("Start stream error for %s: %s", camera_id, e)
        return error(str(e), 500)


@cameras_bp.post("/<camera_id>/stream/stop")
@require_auth
def stop_stream(camera_id: str):
    try:
        from backend.app.api.v1.cameras.tasks import stop_camera_stream
        result = stop_camera_stream(camera_id)
        return success(result, "Stream stop signal sent")
    except Exception as e:
        return error(str(e), 500)


@cameras_bp.get("/<camera_id>/stream/status")
@require_auth
def stream_status(camera_id: str):
    try:
        from pathlib import Path
        playlist = Path(f"/tmp/hls/{camera_id}/stream.m3u8")
        is_active = playlist.exists()
        return success({
            "camera_id": camera_id,
            "active": is_active,
            "playlist_url": f"/streams/{camera_id}/stream.m3u8" if is_active else None,
        })
    except Exception as e:
        return error(str(e), 500)


@cameras_bp.get("/<camera_id>/stream/hls/<filename>")
def serve_hls_segment(camera_id: str, filename: str):
    """Serve HLS segments without auth (required for hls.js)."""
    import re
    from flask import send_from_directory
    # Validate filename to prevent path traversal
    if not re.match(r'^[a-zA-Z0-9_\-\.]+\.(m3u8|ts)$', filename):
        return error("Invalid filename", 400)
    hls_dir = f"/tmp/hls/{camera_id}"
    return send_from_directory(hls_dir, filename)
