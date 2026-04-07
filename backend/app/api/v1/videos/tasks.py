"""Video processing Celery tasks.

Pipeline:
    Upload -> R2 storage -> extract_frames (FFmpeg) -> quality_filter -> frames ready for annotation
"""
import logging
import os
import subprocess
import tempfile
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_celery():
    try:
        from backend.app.infrastructure.queue.celery_app import get_celery
        return get_celery()
    except Exception:
        return None


def _get_r2_storage():
    """Get R2 storage instance. Returns None if not configured."""
    try:
        from backend.app.infrastructure.storage.r2_storage import R2Storage
        account_id = os.environ.get("R2_ACCOUNT_ID", "")
        access_key = os.environ.get("R2_ACCESS_KEY_ID", "")
        secret_key = os.environ.get("R2_SECRET_ACCESS_KEY", "")
        bucket = os.environ.get("R2_BUCKET_NAME", "epi-monitor")
        endpoint = os.environ.get("R2_ENDPOINT_URL", "")
        if not (account_id and access_key and secret_key):
            return None
        return R2Storage(account_id, access_key, secret_key, bucket, endpoint)
    except Exception as e:
        logger.warning("R2 storage unavailable: %s", e)
        return None


def dispatch_extract_frames(video_id: str, storage_key: str) -> dict:
    """Dispatch frame extraction task (async if Celery available, else degraded)."""
    celery = _get_celery()
    if celery and _extract_frames_task is not None:
        result = _extract_frames_task.apply_async(
            args=[video_id, storage_key],
            queue="extraction",
        )
        return {"status": "queued", "task_id": result.id}
    else:
        logger.warning("Celery unavailable — frame extraction deferred")
        return {"status": "degraded", "message": "Configure Redis+Celery for async extraction"}


def _run_ffmpeg_scene_detection(input_path: str, output_dir: str) -> list:
    """Extract frames at scene changes using FFmpeg. Returns list of frame paths."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_pattern = str(output_dir / "frame_%04d.jpg")

    cmd = [
        "ffmpeg", "-i", input_path,
        "-vf", "select='gt(scene\\,0.3)'",
        "-vsync", "vfr",
        "-q:v", "2",
        output_pattern,
    ]

    try:
        subprocess.run(cmd, capture_output=True, check=True, timeout=300)
        frames = sorted(output_dir.glob("frame_*.jpg"))
        logger.info("Extracted %d frames from %s", len(frames), input_path)
        return [str(f) for f in frames]
    except FileNotFoundError:
        logger.error("ffmpeg not found — frame extraction unavailable")
        return []
    except subprocess.CalledProcessError as e:
        logger.error("FFmpeg failed: %s", e.stderr.decode())
        return []
    except subprocess.TimeoutExpired:
        logger.error("FFmpeg timed out processing %s", input_path)
        return []


def _compute_quality_score(frame_path: str) -> float:
    """Simple quality score based on file size (proxy for detail level). 0.0-1.0."""
    try:
        size = Path(frame_path).stat().st_size
        # Frames below 5KB are likely blank/black; above 100KB are high quality
        score = min(1.0, max(0.0, (size - 5000) / 95000))
        return round(score, 3)
    except Exception:
        return 0.5


# Register Celery tasks if available
try:
    from backend.app.infrastructure.queue.celery_app import create_celery
    _celery = create_celery()

    if _celery:
        @_celery.task(name="videos.extract_frames", queue="extraction", bind=True, max_retries=2)
        def _extract_frames_task(self, video_id: str, storage_key: str):
            """Download video from R2, extract frames via FFmpeg, save to DB."""
            from backend.app.infrastructure.database.connection import db_pool

            # Update status to processing
            try:
                with db_pool.get_cursor() as cur:
                    cur.execute(
                        "UPDATE training_videos SET status = 'processing' WHERE id = %s",
                        (video_id,),
                    )
            except Exception as e:
                logger.warning("DB status update failed: %s", e)

            storage = _get_r2_storage()
            frames_inserted = 0

            with tempfile.TemporaryDirectory() as tmpdir:
                video_path = os.path.join(tmpdir, "video.mp4")

                # Download from R2
                if storage:
                    try:
                        url = storage.get_presigned_url(storage_key)
                        if url:
                            import requests
                            resp = requests.get(url, timeout=60)
                            resp.raise_for_status()
                            with open(video_path, "wb") as f:
                                f.write(resp.content)
                            logger.info("Downloaded video %s", video_id)
                        else:
                            logger.warning("Could not get presigned URL for %s", storage_key)
                            video_path = None
                    except Exception as e:
                        logger.error("Download failed for %s: %s", video_id, e)
                        video_path = None
                else:
                    video_path = None

                if video_path and os.path.exists(video_path):
                    frames_dir = os.path.join(tmpdir, "frames")
                    frame_paths = _run_ffmpeg_scene_detection(video_path, frames_dir)

                    for idx, frame_path in enumerate(frame_paths):
                        frame_id = str(uuid.uuid4())
                        quality = _compute_quality_score(frame_path)

                        # Upload frame to R2 if storage available
                        frame_key = None
                        if storage and quality > 0.1:
                            try:
                                with open(frame_path, "rb") as f:
                                    frame_key = storage.upload(
                                        f"frames/{video_id}/{frame_id}.jpg",
                                        f.read(),
                                        "image/jpeg",
                                    )
                            except Exception as e:
                                logger.debug("Frame upload failed: %s", e)

                        # Insert frame record
                        try:
                            with db_pool.get_cursor() as cur:
                                cur.execute(
                                    """
                                    INSERT INTO training_frames
                                        (id, video_id, user_id, frame_number, storage_key, quality_score)
                                    SELECT %s, %s, user_id, %s, %s, %s
                                    FROM training_videos WHERE id = %s
                                    """,
                                    (frame_id, video_id, idx, frame_key, quality, video_id),
                                )
                                frames_inserted += 1
                        except Exception as e:
                            logger.warning("Frame insert failed: %s", e)

            # Update video status to ready
            try:
                with db_pool.get_cursor() as cur:
                    cur.execute(
                        "UPDATE training_videos SET status = 'ready', frame_count = %s, processed_at = NOW() WHERE id = %s",
                        (frames_inserted, video_id),
                    )
            except Exception as e:
                logger.warning("Final status update failed: %s", e)

            logger.info("Video %s: %d frames extracted", video_id, frames_inserted)
            return {"video_id": video_id, "frames_extracted": frames_inserted}
    else:
        _extract_frames_task = None

except Exception as e:
    logger.warning("Celery task registration skipped: %s", e)
    _extract_frames_task = None
