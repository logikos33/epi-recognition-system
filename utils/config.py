"""
Configuration Management for EPI Recognition System
"""
import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Base Directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Database Configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres@localhost:5432/epi_monitoring"
)

# YOLO Model Configuration
YOLO_MODEL_PATH = os.getenv(
    "YOLO_MODEL_PATH",
    str(BASE_DIR / "models" / "yolov8n.pt")
)
DETECTION_CONFIDENCE_THRESHOLD = float(os.getenv("DETECTION_CONFIDENCE_THRESHOLD", "0.5"))
IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", "0.45"))

# Camera Configuration
CAMERA_RTSP_URLS = os.getenv("CAMERA_RTSP_URLS", "").split(",") if os.getenv("CAMERA_RTSP_URLS") else []
MAX_CAMERAS = int(os.getenv("MAX_CAMERAS", "4"))

# Storage Configuration
STORAGE_DIR = BASE_DIR / "storage"
IMAGES_DIR = STORAGE_DIR / "images"
ANNOTATED_IMAGES_DIR = STORAGE_DIR / "annotated"
REPORTS_DIR = STORAGE_DIR / "reports"

# Create directories if they don't exist
for directory in [STORAGE_DIR, IMAGES_DIR, ANNOTATED_IMAGES_DIR, REPORTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_FILE = STORAGE_DIR / "epi_system.log"

# Processing Configuration
FRAME_EXTRACTION_INTERVAL = int(os.getenv("FRAME_EXTRACTION_INTERVAL", "1"))  # seconds
MAX_PROCESSING_THREADS = int(os.getenv("MAX_PROCESSING_THREADS", "4"))
BATCH_SIZE = int(os.getenv("BATCH_SIZE", "8"))

# EPI Types to Detect
EPI_TYPES = {
    "helmet": {"required": True, "label": "Capacete"},
    "gloves": {"required": True, "label": "Luvas"},
    "glasses": {"required": True, "label": "Óculos"},
    "vest": {"required": True, "label": "Colete"},
    "boots": {"required": False, "label": "Botas"}
}

# Alert Configuration
ALERT_SEVERITY_THRESHOLDS = {
    "critical": 0.0,  # Missing any required EPI
    "high": 0.3,      # Low compliance rate
    "medium": 0.6,    # Medium compliance rate
    "low": 0.8        # High compliance rate but not perfect
}

# Streamlit Configuration
STREAMLIT_HOST = os.getenv("STREAMLIT_HOST", "localhost")
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
STREAMLIT_TITLE = "Sistema de Monitoramento de EPI"
STREAMLIT_LAYOUT = "wide"

# Application Configuration
APP_NAME = "EPI Recognition System"
APP_VERSION = "1.0.0"
DEBUG = os.getenv("DEBUG", "False").lower() == "true"

# Time Configuration
TIMEZONE = os.getenv("TIMEZONE", "America/Sao_Paulo")

# Reporting Configuration
REPORT_FORMATS = ["pdf", "csv", "json"]
DEFAULT_REPORT_FORMAT = "pdf"


class Config:
    """Main configuration class"""

    def __init__(self):
        self.database_url = DATABASE_URL
        self.yolo_model_path = YOLO_MODEL_PATH
        self.detection_confidence_threshold = DETECTION_CONFIDENCE_THRESHOLD
        self.iou_threshold = IOU_THRESHOLD
        self.camera_rtsp_urls = CAMERA_RTSP_URLS
        self.max_cameras = MAX_CAMERAS
        self.storage_dir = STORAGE_DIR
        self.images_dir = IMAGES_DIR
        self.annotated_images_dir = ANNOTATED_IMAGES_DIR
        self.reports_dir = REPORTS_DIR
        self.log_level = LOG_LEVEL
        self.log_format = LOG_FORMAT
        self.log_file = LOG_FILE
        self.frame_extraction_interval = FRAME_EXTRACTION_INTERVAL
        self.max_processing_threads = MAX_PROCESSING_THREADS
        self.batch_size = BATCH_SIZE
        self.epi_types = EPI_TYPES
        self.alert_severity_thresholds = ALERT_SEVERITY_THRESHOLDS
        self.streamlit_host = STREAMLIT_HOST
        self.streamlit_port = STREAMLIT_PORT
        self.streamlit_title = STREAMLIT_TITLE
        self.streamlit_layout = STREAMLIT_LAYOUT
        self.app_name = APP_NAME
        self.app_version = APP_VERSION
        self.debug = DEBUG
        self.timezone = TIMEZONE
        self.report_formats = REPORT_FORMATS
        self.default_report_format = DEFAULT_REPORT_FORMAT

    def __repr__(self):
        return f"<Config(app_name={self.app_name}, version={self.app_version}, debug={self.debug})>"


# Global configuration instance
config = Config()


def get_config() -> Config:
    """
    Get the global configuration instance
    Returns:
        Config: Global configuration object
    """
    return config
