"""
EPI Monitor — Generic RTSP Protocol

Adaptador genérico para câmeras RTSP sem fabricante específico.
"""

import cv2
from typing import List
from .base import AbstractCameraProtocol
from cameras.models import Channel


class GenericRTSPProtocol(AbstractCameraProtocol):
    """Protocolo genérico para câmeras RTSP."""

    TIMEOUT = 10

    def build_rtsp_url(self, host: str, port: int, username: str,
                       password: str, channel: int,
                       subtype: int) -> str:
        """Primeira URL RTSP comum a tentar."""
        return f"rtsp://{username}:{password}@{host}:{port}/stream1"

    def build_snapshot_url(self, host: str, port: int,
                           username: str, password: str,
                           channel: int) -> str:
        """Tenta HTTP snapshot (muitas câmeras suportam)."""
        return f"http://{host}:{port}/snapshot.cgi"

    def discover_channels(self, host: str, port: int,
                          username: str,
                          password: str) -> List[Channel]:
        """Retorna canal único para câmeras genéricas."""
        return [Channel(
            number=1,
            name="Canal 1",
            status="unknown",
            has_signal=False
        )]

    def get_manufacturer_name(self) -> str:
        return "Generic"

    def test_urls(self, urls: List[str]) -> tuple:
        """Testa múltiplas URLs RTSP e retorna a primeira que funciona."""
        for url in urls:
            try:
                cap = cv2.VideoCapture(url)
                if cap.isOpened():
                    ret, frame = cap.read()
                    cap.release()
                    if ret:
                        return True, url
            except Exception:
                continue
        return False, None
