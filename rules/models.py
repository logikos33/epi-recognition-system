"""
Data classes para Rules Engine.
"""
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


@dataclass
class Rule:
    """Regra de negócio para processamento de detecções."""

    id: str
    name: str
    description: Optional[str] = None
    template_type: Optional[str] = None  # product_count, bay_control, plate_capture, epi_compliance
    event_type: str = 'detection'  # detection, no_detection
    event_config: Dict[str, Any] = field(default_factory=dict)
    action_type: str = 'count_product'  # start_session, end_session, count_product, associate_plate
    action_config: Dict[str, Any] = field(default_factory=dict)
    camera_ids: Optional[list] = None  # null = todas as câmeras
    cooldown_seconds: int = 0
    min_confidence: float = 0.5
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: tuple) -> 'Rule':
        """Cria Rule a partir de uma linha do banco."""
        return cls(
            id=str(row[0]),
            name=row[1],
            description=row[2],
            template_type=row[3],
            event_type=row[4],
            event_config=row[5] or {},
            action_type=row[6],
            action_config=row[7] or {},
            camera_ids=row[8],
            cooldown_seconds=row[9],
            min_confidence=float(row[10]),
            is_active=row[11],
            created_at=row[12],
            updated_at=row[13]
        )


@dataclass
class CountingSession:
    """Sessão de contagem de produtos."""

    id: str
    user_id: str
    camera_id: Optional[str] = None
    bay_id: Optional[str] = None
    truck_plate: Optional[str] = None
    product_class_id: Optional[int] = None
    product_count: int = 0
    ai_count: int = 0
    operator_count: Optional[int] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    status: str = 'active'  # active, pending_validation, validated, rejected
    validated_by: Optional[str] = None
    validated_at: Optional[datetime] = None
    validation_notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_row(cls, row: tuple) -> 'CountingSession':
        """Cria CountingSession a partir de uma linha do banco."""
        return cls(
            id=str(row[0]),
            user_id=str(row[1]),
            camera_id=str(row[2]) if row[2] else None,
            bay_id=row[3],
            truck_plate=row[4],
            product_class_id=row[5],
            product_count=row[6] or 0,
            ai_count=row[7] or 0,
            operator_count=row[8],
            started_at=row[9],
            ended_at=row[10],
            duration_seconds=row[11],
            status=row[12],
            validated_by=row[13],
            validated_at=row[14],
            validation_notes=row[15],
            metadata=row[16] or {}
        )


@dataclass
class SessionEvent:
    """Evento de uma sessão."""

    id: str
    session_id: str
    event_type: str  # detection, count, plate_captured, session_started, session_ended
    class_name: Optional[str] = None
    confidence: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)
    occurred_at: Optional[datetime] = None

    @classmethod
    def from_row(cls, row: tuple) -> 'SessionEvent':
        """Cria SessionEvent a partir de uma linha do banco."""
        return cls(
            id=str(row[0]),
            session_id=str(row[1]),
            event_type=row[2],
            class_name=row[3],
            confidence=float(row[4]) if row[4] else None,
            details=row[5] or {},
            occurred_at=row[6]
        )
