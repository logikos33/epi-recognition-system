from typing import Dict

class RTSPBuilder:
    """Build RTSP URLs based on camera manufacturer"""

    @staticmethod
    def build_url(camera: Dict) -> str:
        """
        Build RTSP URL from camera configuration

        Args:
            camera: Dict with keys: manufacturer, ip, port, username, password, channel, subtype

        Returns:
            Complete RTSP URL string
        """
        manufacturer = camera.get('manufacturer', 'generic')
        ip = camera['ip']
        port = camera.get('port', 554)
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