"""
Camera Helpers - RTSP URL templates and connection utilities for IP cameras
"""
from typing import Dict, Any, Optional
from urllib.parse import quote
from utils.logger import get_logger


class CameraBrand:
    """Camera brand constants"""
    HIKVISION = "hikvision"
    DAHUA = "dahua"
    INTELBRAS = "intelbras"
    GENERIC = "generic"
    AXIS = "axis"
    VIVOTEK = "vivotek"


# RTSP URL Templates by Brand
RTSP_TEMPLATES = {
    CameraBrand.HIKVISION: {
        "main": "rtsp://{username}:{password}@{ip}:{port}/Streaming/Channels/101",
        "sub": "rtsp://{username}:{password}@{ip}:{port}/Streaming/Channels/102",
        "description": "Hikvision IP Camera"
    },
    CameraBrand.DAHUA: {
        "main": "rtsp://{username}:{password}@{ip}:{port}/cam/realmonitor?channel=1&subtype=0",
        "sub": "rtsp://{username}:{password}@{ip}:{port}/cam/realmonitor?channel=1&subtype=1",
        "description": "Dahua IP Camera"
    },
    CameraBrand.INTELBRAS: {
        "main": "rtsp://{username}:{password}@{ip}:{port}/video1",
        "sub": "rtsp://{username}:{password}@{ip}:{port}/video2",
        "description": "Intelbras IP Camera"
    },
    CameraBrand.GENERIC: {
        "main": "rtsp://{username}:{password}@{ip}:{port}/stream",
        "sub": "rtsp://{username}:{password}@{ip}:{port}/stream2",
        "description": "Generic RTSP Camera"
    },
    CameraBrand.AXIS: {
        "main": "rtsp://{username}:{password}@{ip}:{port}/axis-media/media.amp",
        "sub": "rtsp://{username}:{password}@{ip}:{port}/axis-media/media.amp?stream=1",
        "description": "Axis IP Camera"
    },
    CameraBrand.VIVOTEK: {
        "main": "rtsp://{username}:{password}@{ip}:{port}/live.sdp",
        "sub": "rtsp://{username}:{password}@{ip}:{port}/live2.sdp",
        "description": "Vivotek IP Camera"
    },
}


def build_rtsp_url(
    camera: Dict[str, Any],
    stream_type: str = "main"
) -> Optional[str]:
    """
    Build RTSP URL from camera configuration

    Args:
        camera: Camera configuration dictionary with fields:
            - rtsp_url: Pre-built URL (if available)
            - ip_address: IP address
            - rtsp_port: RTSP port (default 554)
            - rtsp_username: Username
            - rtsp_password: Password
            - camera_brand: Brand (for template lookup)
        stream_type: Stream type ("main" or "sub")

    Returns:
        Complete RTSP URL or None if missing required fields
    """
    logger = get_logger(__name__)

    # If pre-built URL exists, use it
    if camera.get('rtsp_url'):
        return camera['rtsp_url']

    # Get required fields
    ip = camera.get('ip_address') or camera.get('rtsp_ip')
    port = camera.get('rtsp_port', 554)
    username = camera.get('rtsp_username')
    password = camera.get('rtsp_password')
    brand = camera.get('camera_brand', CameraBrand.GENERIC).lower()

    # Validate required fields
    if not ip:
        logger.error("Missing IP address for camera")
        return None

    if not username:
        logger.error(f"Missing username for camera at {ip}")
        return None

    if not password:
        logger.error(f"Missing password for camera at {ip}")
        return None

    # URL encode credentials (special characters)
    encoded_username = quote(username, safe='')
    encoded_password = quote(password, safe='')

    # Get template for brand
    brand_key = brand.lower()
    if brand_key not in RTSP_TEMPLATES:
        logger.warning(f"Unknown brand '{brand}', using generic template")
        brand_key = CameraBrand.GENERIC

    template = RTSP_TEMPLATES[brand_key].get(stream_type, RTSP_TEMPLATES[brand_key]["main"])

    # Build URL
    try:
        rtsp_url = template.format(
            username=encoded_username,
            password=encoded_password,
            ip=ip,
            port=port
        )
        logger.debug(f"Built RTSP URL for {brand} camera at {ip}")
        return rtsp_url
    except Exception as e:
        logger.error(f"Error building RTSP URL: {e}")
        return None


def test_rtsp_connection(rtsp_url: str, timeout: int = 5) -> tuple[bool, str]:
    """
    Test RTSP connection

    Args:
        rtsp_url: RTSP URL to test
        timeout: Connection timeout in seconds

    Returns:
        Tuple of (success: bool, message: str)
    """
    import cv2

    logger = get_logger(__name__)

    try:
        logger.info(f"Testing RTSP connection: {rtsp_url}")
        cap = cv2.VideoCapture(rtsp_url)

        if not cap.isOpened():
            return False, "Failed to open RTSP stream"

        # Set timeout
        cap.set(cv2.CAP_PROP_FPS, 30)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        # Try to read a frame
        ret, frame = cap.read()
        cap.release()

        if not ret or frame is None:
            return False, "Could not read frame from stream"

        height, width = frame.shape[:2]
        return True, f"Connected successfully ({width}x{height})"

    except ImportError:
        logger.error("OpenCV not installed")
        return False, "OpenCV not available for RTSP testing"
    except Exception as e:
        logger.error(f"RTSP connection error: {e}")
        return False, f"Connection failed: {str(e)}"


def parse_camera_brand_from_url(rtsp_url: str) -> str:
    """
    Try to guess camera brand from RTSP URL pattern

    Args:
        rtsp_url: RTSP URL

    Returns:
        Camera brand string
    """
    url_lower = rtsp_url.lower()

    if "channels/10" in url_lower or "hikvision" in url_lower:
        return CameraBrand.HIKVISION
    elif "cam/realmonitor" in url_lower or "dahua" in url_lower:
        return CameraBrand.DAHUA
    elif "/video1" in url_lower or "intelbras" in url_lower:
        return CameraBrand.INTELBRAS
    elif "axis-media" in url_lower or "axis" in url_lower:
        return CameraBrand.AXIS
    elif "live.sdp" in url_lower or "vivotek" in url_lower:
        return CameraBrand.VIVOTEK
    else:
        return CameraBrand.GENERIC


def get_camera_connection_string(camera: Dict[str, Any]) -> str:
    """
    Get human-readable connection string for camera

    Args:
        camera: Camera configuration

    Returns:
        Connection string like "rtsp://user:***@192.168.1.100:554/stream"
    """
    rtsp_url = build_rtsp_url(camera)
    if rtsp_url:
        # Hide password
        if '@' in rtsp_url:
            parts = rtsp_url.split('@')
            auth = parts[0].split(':')[-2:]  # Get username:password part
            if len(auth) >= 2:
                return rtsp_url.replace(auth[1], '***')
        return rtsp_url
    return "Not configured"


def validate_camera_config(camera: Dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate camera configuration

    Args:
        camera: Camera configuration dictionary

    Returns:
        Tuple of (is_valid: bool, errors: list[str])
    """
    errors = []

    # Check required fields
    if not camera.get('name'):
        errors.append("Camera name is required")

    if not camera.get('location'):
        errors.append("Location is required")

    # Check RTSP configuration
    has_prebuilt_url = bool(camera.get('rtsp_url'))

    if not has_prebuilt_url:
        if not camera.get('ip_address') and not camera.get('rtsp_ip'):
            errors.append("IP address is required (or pre-built RTSP URL)")

        if not camera.get('rtsp_username'):
            errors.append("RTSP username is required")

        if not camera.get('rtsp_password'):
            errors.append("RTSP password is required")

    # Validate brand
    brand = camera.get('camera_brand', '').lower()
    if brand and brand not in [b.lower() for b in RTSP_TEMPLATES.keys()]:
        errors.append(f"Unknown camera brand: {brand}")

    # Validate port
    port = camera.get('rtsp_port', 554)
    if not isinstance(port, int) or port < 1 or port > 65535:
        errors.append("Invalid RTSP port")

    return len(errors) == 0, errors


def get_supported_brands() -> list[str]:
    """
    Get list of supported camera brands

    Returns:
        List of brand names
    """
    return [
        (brand, RTSP_TEMPLATES[brand]["description"])
        for brand in RTSP_TEMPLATES.keys()
    ]
