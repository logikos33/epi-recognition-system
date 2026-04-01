"""
EPI Monitor — Camera Protocol Base

Interface base para todos os adaptadores de fabricante.
"""

from abc import ABC, abstractmethod
from typing import List
from cameras.models import Channel, ConnectionResult


class AbstractCameraProtocol(ABC):
    """Interface base para todos os fabricantes de câmera."""

    @abstractmethod
    def build_rtsp_url(self, host: str, port: int, username: str,
                       password: str, channel: int,
                       subtype: int) -> str:
        """Constrói URL RTSP para câmera."""
        ...

    @abstractmethod
    def build_snapshot_url(self, host: str, port: int,
                           username: str, password: str,
                           channel: int) -> str:
        """Constrói URL para snapshot JPEG."""
        ...

    @abstractmethod
    def discover_channels(self, host: str, port: int,
                          username: str,
                          password: str) -> List[Channel]:
        """Descobre canais disponíveis no DVR/NVR."""
        ...

    @abstractmethod
    def get_manufacturer_name(self) -> str:
        """Retorna nome do fabricante."""
        ...

    def get_supported_models(self) -> List[str]:
        """Retorna lista de modelos suportados."""
        return []
