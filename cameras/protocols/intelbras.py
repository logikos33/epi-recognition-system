"""
EPI Monitor — Intelbras Camera Protocol

Adaptador para câmeras Intelbras (usa SDK Dahua).
"""

import requests
from requests.auth import HTTPDigestAuth
from typing import List
from .base import AbstractCameraProtocol
from cameras.models import Channel, ConnectionResult


class IntelbrasProtocol(AbstractCameraProtocol):
    """Protocolo para câmeras Intelbras/Dahua."""

    TIMEOUT = 10

    def build_rtsp_url(self, host: str, port: int, username: str,
                       password: str, channel: int,
                       subtype: int) -> str:
        """URL RTSP padrão Intelbras: cam/realmonitor"""
        return f"rtsp://{username}:{password}@{host}:{port}/cam/realmonitor?channel={channel}&subtype={subtype}"

    def build_snapshot_url(self, host: str, port: int,
                           username: str, password: str,
                           channel: int) -> str:
        """URL de snapshot via CGI."""
        return f"http://{host}:{port}/cgi-bin/snapshot.cgi?channel={channel}"

    def discover_channels(self, host: str, port: int,
                          username: str,
                          password: str) -> List[Channel]:
        """Descobre canais via CGI Dahua."""
        channels = []
        try:
            # Tentar detectar até 16 canais
            for ch in range(1, 17):
                url = f"http://{host}:{port}/cgi-bin/snapshot.cgi?channel={ch}"
                resp = requests.get(url, auth=HTTPDigestAuth(username, password),
                                   timeout=5)
                if resp.status_code == 200:
                    channels.append(Channel(
                        number=ch,
                        name=f"Canal {ch}",
                        status="online",
                        has_signal=len(resp.content) > 1000
                    ))
                elif resp.status_code == 401:
                    # Auth error - parar
                    break
        except Exception:
            pass
        return channels

    def get_manufacturer_name(self) -> str:
        return "Intelbras"

    def get_supported_models(self) -> List[str]:
        return ["DVR", "NVR", "IP Camera"]
