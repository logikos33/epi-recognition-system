"""Camera Celery tasks — HLS streaming + YOLO inference loop.

Architecture:
    Worker: FFmpeg (RTSP→HLS) + YOLO detections → Redis pub/sub
    API: Redis subscriber → SocketIO → Browser

    Worker never speaks WebSocket directly.
    Redis channel: det:{camera_id}
"""
import logging
import os
import subprocess
import time
from pathlib import Path

logger = logging.getLogger(__name__)


def get_celery():
    """Get Celery instance with graceful degradation."""
    try:
        from backend.app.infrastructure.queue.celery_app import get_celery as _get
        return _get()
    except Exception:
        return None


def _get_redis_client():
    """Get Redis client for pub/sub. Returns None if unavailable."""
    try:
        import redis
        url = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
        return redis.from_url(url, decode_responses=True)
    except Exception as e:
        logger.warning("Redis unavailable: %s", e)
        return None


def _try_load_yolo(model_path: str):
    """Load YOLO model with graceful degradation."""
    try:
        from ultralytics import YOLO
        if not os.path.exists(model_path):
            logger.warning("YOLO model not found at %s — inference degraded", model_path)
            return None
        model = YOLO(model_path)
        logger.info("YOLO model loaded: %s", model_path)
        return model
    except ImportError:
        logger.warning("ultralytics not installed — YOLO inference degraded")
        return None
    except Exception as e:
        logger.warning("YOLO load failed — inference degraded: %s", e)
        return None


class HLSStreamManager:
    """Manages a single FFmpeg process for HLS output."""

    def __init__(self, camera_id: str, rtsp_url: str):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.process: subprocess.Popen | None = None
        self.output_dir = Path(f"/tmp/hls/{camera_id}")

    @property
    def playlist_path(self) -> str:
        return str(self.output_dir / "stream.m3u8")

    def start(self) -> bool:
        """Start FFmpeg RTSP→HLS transcoding. Returns True if started."""
        from backend.app.core.validators import RTSPUrlValidator
        from backend.app.core.exceptions import RTSPValidationError
        try:
            RTSPUrlValidator.validate(self.rtsp_url)
        except RTSPValidationError as e:
            logger.error("RTSP validation failed for %s: %s", self.camera_id, e)
            return False

        self.output_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-y",
            "-rtsp_transport", "tcp",
            "-i", self.rtsp_url,
            "-c:v", "libx264",
            "-preset", os.environ.get("FFMPEG_PRESET", "ultrafast"),
            "-b:v", os.environ.get("FFMPEG_VIDEO_BITRATE", "512k"),
            "-s", os.environ.get("FFMPEG_RESOLUTION", "640x360"),
            "-f", "hls",
            "-hls_time", str(os.environ.get("HLS_SEGMENT_DURATION", "1")),
            "-hls_list_size", str(os.environ.get("HLS_PLAYLIST_SIZE", "3")),
            "-hls_flags", "delete_segments+append_list",
            str(self.output_dir / "stream.m3u8"),
        ]

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
            logger.info("FFmpeg started for camera %s (pid=%d)", self.camera_id, self.process.pid)
            return True
        except FileNotFoundError:
            logger.error("ffmpeg not found — streaming unavailable")
            return False
        except Exception as e:
            logger.error("FFmpeg start failed for %s: %s", self.camera_id, e)
            return False

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            logger.info("FFmpeg stopped for camera %s", self.camera_id)
        self.process = None


def start_camera_stream(camera_id: str, rtsp_url: str) -> dict:
    """
    Start HLS stream + YOLO inference for a camera.

    Can be called directly (sync) or dispatched as Celery task.
    Returns status dict.
    """
    celery = get_celery()
    if celery and _camera_stream_task is not None:
        result = _camera_stream_task.apply_async(
            args=[camera_id, rtsp_url],
            queue="inference",
        )
        return {"status": "started", "task_id": result.id}
    else:
        logger.warning("Celery unavailable — running stream sync (dev mode)")
        return {"status": "degraded", "message": "Celery unavailable, use Redis+Celery for production"}


def stop_camera_stream(camera_id: str) -> dict:
    """Signal a camera stream to stop via Redis."""
    r = _get_redis_client()
    if r:
        r.set(f"stream:stop:{camera_id}", "1", ex=30)
        logger.info("Stop signal sent for camera %s", camera_id)
        return {"status": "stopping"}
    return {"status": "error", "message": "Redis unavailable"}


def _run_inference_loop(camera_id: str, model, redis_client, stop_key: str) -> None:
    """Run YOLO inference on HLS frames and publish to Redis."""
    output_dir = Path(f"/tmp/hls/{camera_id}")
    fps_interval = 1.0 / int(os.environ.get("YOLO_FPS", "5"))
    confidence = float(os.environ.get("DETECTION_CONFIDENCE_THRESHOLD", "0.5"))

    logger.info("Inference loop started for camera %s", camera_id)

    while True:
        # Check stop signal
        if redis_client.get(stop_key):
            redis_client.delete(stop_key)
            logger.info("Inference loop stopped for camera %s", camera_id)
            break

        # Find latest frame from HLS segments
        frames = sorted(output_dir.glob("*.ts"))
        if not frames:
            time.sleep(0.5)
            continue

        try:
            latest = frames[-1]
            results = model(str(latest), conf=confidence, verbose=False)
            detections = []
            for r in results:
                for box in r.boxes:
                    x1, y1, x2, y2 = box.xyxyn[0].tolist()
                    detections.append({
                        "class": r.names[int(box.cls)],
                        "confidence": float(box.conf),
                        "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2},
                    })

            if detections:
                import json
                payload = json.dumps({
                    "camera_id": camera_id,
                    "timestamp": time.time(),
                    "detections": detections,
                })
                redis_client.publish(f"det:{camera_id}", payload)
        except Exception as e:
            logger.debug("Inference frame error (non-fatal): %s", e)

        time.sleep(fps_interval)


# Celery task (registered only if Celery is available)
_camera_stream_task = None

try:
    from backend.app.infrastructure.queue.celery_app import create_celery
    _celery = create_celery()

    if _celery:
        @_celery.task(name="cameras.stream", queue="inference", bind=True, max_retries=3)
        def _camera_stream_task(self, camera_id: str, rtsp_url: str):
            """Celery task: manage HLS stream + YOLO inference for one camera."""
            stop_key = f"stream:stop:{camera_id}"
            redis_client = _get_redis_client()
            model_path = os.environ.get("YOLO_MODEL_PATH", "models/yolov8n.pt")
            model = _try_load_yolo(model_path)

            stream = HLSStreamManager(camera_id, rtsp_url)
            started = stream.start()

            if not started:
                logger.error("Failed to start HLS for camera %s", camera_id)
                return {"status": "error", "camera_id": camera_id}

            restart_count = 0
            max_restarts = int(os.environ.get("MAX_STREAM_RESTARTS", "3"))

            while restart_count <= max_restarts:
                if redis_client and redis_client.get(stop_key):
                    redis_client.delete(stop_key)
                    break

                if not stream.is_running():
                    restart_count += 1
                    if restart_count > max_restarts:
                        logger.error("Camera %s exceeded max restarts", camera_id)
                        break
                    logger.warning("Stream died for %s — restart %d/%d", camera_id, restart_count, max_restarts)
                    stream.start()

                if model and redis_client:
                    try:
                        _run_inference_loop(camera_id, model, redis_client, stop_key)
                    except Exception as e:
                        logger.warning("Inference loop error for %s: %s", camera_id, e)
                else:
                    # No YOLO or Redis — just keep FFmpeg running, check stop signal
                    time.sleep(5)
                    if redis_client and redis_client.get(stop_key):
                        break

            stream.stop()
            return {"status": "stopped", "camera_id": camera_id, "restarts": restart_count}

except Exception as e:
    logger.warning("Celery task registration skipped (degraded): %s", e)
