"""
Pydantic Schemas for Request/Response Validation
"""
from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, validator


# Camera Schemas
class CameraBase(BaseModel):
    """Base schema for Camera"""
    name: str = Field(..., min_length=1, max_length=255)
    location: str = Field(..., min_length=1, max_length=255)
    rtsp_url: str = Field(..., min_length=1, max_length=500)
    is_active: bool = True


class CameraCreate(CameraBase):
    """Schema for creating a camera"""
    pass


class CameraUpdate(BaseModel):
    """Schema for updating a camera"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    location: Optional[str] = Field(None, min_length=1, max_length=255)
    rtsp_url: Optional[str] = Field(None, min_length=1, max_length=500)
    is_active: Optional[bool] = None


class CameraResponse(CameraBase):
    """Schema for camera response"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# EPI Type Schemas
class EPITypeBase(BaseModel):
    """Base schema for EPI Type"""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    required: bool = True


class EPITypeCreate(EPITypeBase):
    """Schema for creating an EPI type"""
    pass


class EPITypeUpdate(BaseModel):
    """Schema for updating an EPI type"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    required: Optional[bool] = None


class EPITypeResponse(EPITypeBase):
    """Schema for EPI type response"""
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# Detection Schemas
class DetectionBase(BaseModel):
    """Base schema for Detection"""
    camera_id: int
    epis_detected: Dict[str, bool] = Field(..., description="Dictionary of detected EPIs")
    confidence: float = Field(..., ge=0.0, le=1.0)
    is_compliant: bool = False
    person_count: int = Field(default=0, ge=0)


class DetectionCreate(DetectionBase):
    """Schema for creating a detection"""
    image_path: Optional[str] = None
    bbox_data: Optional[Dict[str, Any]] = None


class DetectionUpdate(BaseModel):
    """Schema for updating a detection"""
    is_compliant: Optional[bool] = None
    is_resolved: Optional[bool] = None


class DetectionResponse(DetectionBase):
    """Schema for detection response"""
    id: int
    timestamp: datetime
    image_path: Optional[str] = None
    bbox_data: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


# Alert Schemas
class AlertBase(BaseModel):
    """Base schema for Alert"""
    detection_id: int
    severity: str = Field(..., pattern="^(low|medium|high|critical)$")
    message: str = Field(..., min_length=1, max_length=500)


class AlertCreate(AlertBase):
    """Schema for creating an alert"""
    pass


class AlertResponse(AlertBase):
    """Schema for alert response"""
    id: int
    is_resolved: bool
    created_at: datetime
    resolved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Analytics Schemas
class ComplianceStats(BaseModel):
    """Schema for compliance statistics"""
    total_detections: int
    compliant_detections: int
    non_compliant_detections: int
    compliance_rate: float
    epi_detection_rates: Dict[str, float]


class CameraStats(BaseModel):
    """Schema for camera-specific statistics"""
    camera_id: int
    camera_name: str
    total_detections: int
    compliance_rate: float
    last_detection: Optional[datetime]


class TimeSeriesData(BaseModel):
    """Schema for time series data"""
    timestamp: datetime
    value: float
    label: Optional[str] = None


# Dashboard Data Schemas
class DashboardData(BaseModel):
    """Schema for dashboard overview data"""
    total_cameras: int
    active_cameras: int
    total_detections: int
    compliance_rate: float
    recent_alerts: List[AlertResponse]
    camera_stats: List[CameraStats]
    compliance_over_time: List[TimeSeriesData]


# Detection Result Schema (for internal use)
class BoundingBox(BaseModel):
    """Represents a bounding box"""
    x1: float
    y1: float
    x2: float
    y2: float
    confidence: float
    class_name: str


class DetectionResult(BaseModel):
    """Result from YOLO detection"""
    image_path: str
    detections: List[BoundingBox]
    epis_detected: Dict[str, bool]
    confidence: float
    is_compliant: bool
    timestamp: datetime
    person_count: int
