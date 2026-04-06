"""Application constants and enums."""
from enum import Enum


class CameraManufacturer(str, Enum):
    INTELBRAS = "intelbras"
    HIKVISION = "hikvision"
    GENERIC = "generic"


class StreamStatus(str, Enum):
    STARTING = "starting"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"
    DEGRADED = "degraded"


class TrainingStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoStatus(str, Enum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class AnnotationStatus(str, Enum):
    PENDING = "pending"
    ANNOTATED = "annotated"
    REVIEWED = "reviewed"


# File upload constraints
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv", ".webm"}
MAX_VIDEO_SIZE_BYTES = 500 * 1024 * 1024  # 500MB

# JWT
BEARER_PREFIX = "Bearer "
