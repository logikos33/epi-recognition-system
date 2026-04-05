from typing import Dict
import ipaddress
import logging

logger = logging.getLogger(__name__)


class RTSPBuilder:
    """Build RTSP URLs based on camera manufacturer"""

    # Default RTSP port
    DEFAULT_PORT = 554

    # Supported manufacturers
    SUPPORTED_MANUFACTURERS = {'intelbras', 'hikvision', 'generic'}

    @staticmethod
    def build_url(camera: Dict) -> str:
        """
        Build RTSP URL from camera configuration

        Args:
            camera: Dict with keys: manufacturer, ip, port, username, password, channel, subtype

        Returns:
            Complete RTSP URL string

        Raises:
            ValueError: If required fields are missing or invalid
        """
        # Validate required fields
        if 'ip' not in camera:
            raise ValueError("Camera IP address is required")

        ip = camera['ip']

        # Validate IP address format
        try:
            ipaddress.ip_address(ip)
        except ValueError:
            raise ValueError(f"Invalid IP address format: {ip}")

        manufacturer = camera.get('manufacturer', 'generic')
        if manufacturer not in RTSPBuilder.SUPPORTED_MANUFACTURERS:
            logger.warning(f"Unknown manufacturer '{manufacturer}', using generic")

        port = camera.get('port', RTSPBuilder.DEFAULT_PORT)

        # Validate port range
        if not isinstance(port, int) or not (1 <= port <= 65535):
            raise ValueError(f"Invalid port number: {port}")

        username = camera.get('username', '')
        password = camera.get('password', '')

        # Build auth part
        if username and password:
            auth = f"{username}:{password}@"
        else:
            auth = ''  # No auth

        base = f"rtsp://{auth}{ip}:{port}"

        # Build path based on manufacturer
        if manufacturer == 'intelbras':
            channel = camera.get('channel', 1)
            subtype = camera.get('subtype', 1)
            return f"{base}/cam/realmonitor?channel={channel}&subtype={subtype}"

        elif manufacturer == 'hikvision':
            # Hikvision uses: (channel * 100) + (subtype == 0 ? 1 : 2)
            channel = camera.get('channel', 1)
            subtype = camera.get('subtype', 1)
            stream_id = (channel * 100) + (1 if subtype == 0 else 2)
            return f"{base}/Streaming/Channels/{stream_id}"

        else:  # generic ONVIF
            channel = camera.get('channel', 1)
            return f"{base}/stream{channel}"