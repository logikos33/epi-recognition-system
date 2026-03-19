"""
SQLAlchemy Database Models for EPI Recognition System
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class Camera(Base):
    """
    Represents a surveillance camera in the system
    """
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    rtsp_url = Column(String(500), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship with detections
    detections = relationship("Detection", back_populates="camera", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Camera(id={self.id}, name='{self.name}', location='{self.location}')>"


class EPIType(Base):
    """
    Represents types of EPI (Personal Protective Equipment)
    """
    __tablename__ = "epi_types"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)  # helmet, gloves, glasses, vest, boots
    description = Column(String(500))
    required = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<EPIType(id={self.id}, name='{self.name}', required={self.required})>"


class Detection(Base):
    """
    Represents an EPI detection event from a camera
    """
    __tablename__ = "detections"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    image_path = Column(String(500))
    epis_detected = Column(JSON, nullable=False)  # {"helmet": true, "gloves": false, ...}
    confidence = Column(Float, default=0.0)
    is_compliant = Column(Boolean, default=False, index=True)
    person_count = Column(Integer, default=0)
    bbox_data = Column(JSON)  # Store bounding boxes for visualization

    # Relationship with camera
    camera = relationship("Camera", back_populates="detections")

    def __repr__(self):
        return f"<Detection(id={self.id}, camera_id={self.camera_id}, timestamp={self.timestamp}, is_compliant={self.is_compliant})>"


class Alert(Base):
    """
    Represents alerts generated from non-compliant detections
    """
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    detection_id = Column(Integer, ForeignKey("detections.id"), nullable=False)
    severity = Column(String(50))  # low, medium, high, critical
    message = Column(String(500), nullable=False)
    is_resolved = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime)

    def __repr__(self):
        return f"<Alert(id={self.id}, severity='{self.severity}', is_resolved={self.is_resolved})>"
