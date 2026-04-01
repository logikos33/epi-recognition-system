"""
EPI Monitor — Hikvision Camera Protocol

Adaptador para câmeras Hikvision com ISAPI.
"""

import requests
from requests.auth import HTTPDigestAuth
from typing import List
from .base import AbstractCameraProtocol
from cameras.models import Channel, ConnectionResult


class HikvisionProtocol(AbstractCameraProtocol):
    """Protocolo para câmeras Hikvision."""

    TIMEOUT = 10

    def build_rtsp_url(self, host: str, port: int, username: str,
                       password: str, channel: int,
                       subtype: int) -> str:
        """URL RTSP Hikvision: Streaming/Channels/{N*100+1}"""
        ch_code = channel * 100 + (subtype + 1)
        return f"rtsp://{username}:{password}@{host}:{port}/Streaming/Channels/{ch_code}"

    def build_snapshot_url(self, host: str, port: int,
                           username: str, password: str,
                           channel: int) -> str:
        """URL de snapshot via ISAPI."""
        return f"http://{host}:{port}/ISAPI/Streaming/channels/{channel}01/picture"

    def discover_channels(self, host: str, port: int,
                          username: str,
                          password: str) -> List[Channel]:
        """Descobre canais via ISAPI."""
        channels = []
        try:
            url = f"http://{host}:{port}/ISAPI/System/Video/inputs/channels"
            resp = requests.get(url, auth=HTTPDigestAuth(username, password),
                               timeout=10)
            if resp.status_code == 200:
                # Parse XML de resposta
                import xml.etree.ElementTree as ET
                root = ET.fromstring(resp.content)
                for idx, ch in enumerate(root.findall('.//videoInputChannel')):
                    ch_id = ch.get('id')
                    if ch_id:
                        channels.append(Channel(
                            number=idx + 1,
                            name=f"Canal {ch_id}",
                            status="online",
                            has_signal=True
                        ))
        except Exception:
            # Fallback: tentar até 4 canais padrão
            for ch in range(1, 5):
                channels.append(Channel(
                    number=ch,
                    name=f"Canal {ch}",
                    status="unknown",
                    has_signal=False
                ))
        return channels

    def get_manufacturer_name(self) -> str:
        return "Hikvision"
