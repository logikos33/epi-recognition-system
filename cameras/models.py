"""
EPI Monitor — Camera System Models

Dataclasses para representar câmeras, DVRs e resultados de conexão.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class Camera:
    """Representa uma câmera IP individual."""
    id: str
    name: str
    host: str
    port: int = 554
    username: Optional[str] = None
    channel: int = 1
    subtype: int = 0
    manufacturer: str = 'generic'
    location: Optional[str] = None
    status: str = 'offline'
    is_active: bool = True
    dvr_id: Optional[str] = None
    created_at: Optional[datetime] = None


@dataclass
class DVR:
    """Representa um DVR/NVR com múltiplos canais."""
    id: str
    name: str
    host: str
    manufacturer: str
    port: int = 80
    rtsp_port: int = 554
    username: Optional[str] = None
    status: str = 'offline'


@dataclass
class Channel:
    """Representa um canal de DVR."""
    number: int
    name: str
    status: str
    has_signal: bool = False
    snapshot_base64: Optional[str] = None


@dataclass
class ConnectionResult:
    """Resultado de teste de conexão com câmera."""
    success: bool
    latency_ms: Optional[float] = None
    snapshot_base64: Optional[str] = None
    error: Optional[str] = None
    diagnostics: dict = field(default_factory=dict)
    rtsp_url_used: Optional[str] = None
