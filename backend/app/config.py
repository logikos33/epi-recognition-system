"""Configuration classes using Factory Pattern."""
import os


class BaseConfig:
    SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-in-production")
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-secret-change-in-production")
    JWT_TTL_SECONDS = int(os.environ.get("JWT_TTL_SECONDS", "86400"))  # 24h
    DATABASE_URL = os.environ.get("DATABASE_URL", "")
    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "http://localhost:5173")
    MAX_CONTENT_LENGTH = 500 * 1024 * 1024  # 500MB max upload
    REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # Storage
    R2_ACCOUNT_ID = os.environ.get("R2_ACCOUNT_ID", "")
    R2_ACCESS_KEY_ID = os.environ.get("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET_NAME = os.environ.get("R2_BUCKET_NAME", "epi-monitor")
    R2_ENDPOINT_URL = os.environ.get("R2_ENDPOINT_URL", "")

    # FFmpeg
    FFMPEG_PRESET = os.environ.get("FFMPEG_PRESET", "ultrafast")
    FFMPEG_VIDEO_BITRATE = os.environ.get("FFMPEG_VIDEO_BITRATE", "512k")
    FFMPEG_RESOLUTION = os.environ.get("FFMPEG_RESOLUTION", "640x360")
    HLS_SEGMENT_DURATION = int(os.environ.get("HLS_SEGMENT_DURATION", "1"))
    HLS_PLAYLIST_SIZE = int(os.environ.get("HLS_PLAYLIST_SIZE", "3"))

    # YOLO
    YOLO_MODEL_PATH = os.environ.get("YOLO_MODEL_PATH", "models/yolov8n.pt")
    DETECTION_CONFIDENCE_THRESHOLD = float(os.environ.get("DETECTION_CONFIDENCE_THRESHOLD", "0.5"))
    YOLO_FPS = int(os.environ.get("YOLO_FPS", "5"))


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    TESTING = False


class ProductionConfig(BaseConfig):
    DEBUG = False
    TESTING = False


class TestingConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "postgresql://localhost/epi_monitor_test")


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
