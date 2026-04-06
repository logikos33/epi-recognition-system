"""Videos blueprint — upload, list, process."""
import logging

from flask import Blueprint, g, request

from backend.app.core.auth import require_auth
from backend.app.core.responses import created, error, not_found, success

logger = logging.getLogger(__name__)

videos_bp = Blueprint("videos", __name__, url_prefix="/api/v1/videos")


@videos_bp.get("/")
@require_auth
def list_videos():
    try:
        from backend.app.api.v1.videos.service import VideoService
        videos = VideoService.list_videos(g.user_id)
        return success(videos)
    except Exception as e:
        logger.error("List videos error: %s", e)
        return error("Failed to list videos", 500)


@videos_bp.post("/")
@require_auth
def upload_video():
    try:
        from backend.app.api.v1.videos.service import VideoService
        from backend.app.api.v1.videos.validators import VideoUploadValidator

        if "file" not in request.files:
            return error("No file provided", 422)

        file = request.files["file"]
        VideoUploadValidator.validate(file)

        result = VideoService.create_upload(g.user_id, file)
        return created(result, "Video uploaded successfully")
    except Exception as e:
        logger.error("Upload error: %s", e)
        return error(str(e), 422 if "invalid" in str(e).lower() else 500)


@videos_bp.get("/<video_id>")
@require_auth
def get_video(video_id: str):
    try:
        from backend.app.api.v1.videos.service import VideoService
        video = VideoService.get_video(g.user_id, video_id)
        if not video:
            return not_found("Video")
        return success(video)
    except Exception as e:
        return error("Failed to get video", 500)


@videos_bp.delete("/<video_id>")
@require_auth
def delete_video(video_id: str):
    try:
        from backend.app.api.v1.videos.service import VideoService
        VideoService.delete_video(g.user_id, video_id)
        return success(message="Video deleted")
    except Exception as e:
        return error("Failed to delete video", 500)
