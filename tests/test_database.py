"""
Unit Tests for Database Service
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from services.database_service import DatabaseService, get_database_service
from models.database import Base, Camera, Detection, EPIType, Alert
from models.schemas import (
    CameraCreate, CameraUpdate,
    EPITypeCreate, EPITypeUpdate,
    DetectionCreate,
    AlertCreate
)


class TestDatabaseService:
    """Test suite for DatabaseService"""

    @pytest.fixture
    def db_service(self):
        """Create database service instance with in-memory database"""
        # Use in-memory SQLite for testing
        db_service = DatabaseService("sqlite:///:memory:")

        # Create tables
        Base.metadata.create_all(db_service.engine)

        return db_service

    @pytest.fixture
    def sample_camera(self, db_service):
        """Create a sample camera in database"""
        camera_data = CameraCreate(
            name="Test Camera",
            location="Test Location",
            rtsp_url="rtsp://test",
            is_active=True
        )
        return db_service.create_camera(camera_data)

    @pytest.fixture
    def sample_epi_type(self, db_service):
        """Create sample EPI types in database"""
        epi_data = EPITypeCreate(
            name="helmet",
            description="Capacete de segurança",
            required=True
        )
        return db_service.create_epi_type(epi_data) if hasattr(db_service, 'create_epi_type') else None

    # Camera Tests
    def test_create_camera(self, db_service):
        """Test creating a camera"""
        camera_data = CameraCreate(
            name="Test Camera",
            location="Test Location",
            rtsp_url="rtsp://test",
            is_active=True
        )

        camera = db_service.create_camera(camera_data)

        assert camera is not None
        assert camera.id is not None
        assert camera.name == "Test Camera"
        assert camera.location == "Test Location"
        assert camera.rtsp_url == "rtsp://test"
        assert camera.is_active is True

    def test_get_camera(self, db_service, sample_camera):
        """Test retrieving a camera"""
        camera = db_service.get_camera(sample_camera.id)

        assert camera is not None
        assert camera.id == sample_camera.id
        assert camera.name == sample_camera.name

    def test_get_camera_not_found(self, db_service):
        """Test retrieving non-existent camera"""
        camera = db_service.get_camera(999)

        assert camera is None

    def test_get_all_cameras(self, db_service):
        """Test retrieving all cameras"""
        # Create multiple cameras
        for i in range(3):
            camera_data = CameraCreate(
                name=f"Camera {i}",
                location=f"Location {i}",
                rtsp_url=f"rtsp://test{i}",
                is_active=True
            )
            db_service.create_camera(camera_data)

        cameras = db_service.get_all_cameras()

        assert len(cameras) == 3

    def test_get_all_cameras_active_only(self, db_service):
        """Test retrieving only active cameras"""
        # Create active and inactive cameras
        camera_data1 = CameraCreate(
            name="Active Camera",
            location="Location 1",
            rtsp_url="rtsp://test1",
            is_active=True
        )
        db_service.create_camera(camera_data1)

        camera_data2 = CameraCreate(
            name="Inactive Camera",
            location="Location 2",
            rtsp_url="rtsp://test2",
            is_active=False
        )
        db_service.create_camera(camera_data2)

        cameras = db_service.get_all_cameras(active_only=True)

        assert len(cameras) == 1
        assert cameras[0].name == "Active Camera"

    def test_update_camera(self, db_service, sample_camera):
        """Test updating a camera"""
        update_data = CameraUpdate(name="Updated Camera")

        updated_camera = db_service.update_camera(sample_camera.id, update_data)

        assert updated_camera is not None
        assert updated_camera.name == "Updated Camera"

    def test_update_camera_not_found(self, db_service):
        """Test updating non-existent camera"""
        update_data = CameraUpdate(name="Updated Camera")

        result = db_service.update_camera(999, update_data)

        assert result is None

    def test_delete_camera(self, db_service):
        """Test deleting a camera"""
        camera_data = CameraCreate(
            name="To Delete",
            location="Location",
            rtsp_url="rtsp://test",
            is_active=True
        )
        camera = db_service.create_camera(camera_data)

        success = db_service.delete_camera(camera.id)

        assert success is True

        # Verify camera is deleted
        deleted_camera = db_service.get_camera(camera.id)
        assert deleted_camera is None

    def test_delete_camera_not_found(self, db_service):
        """Test deleting non-existent camera"""
        success = db_service.delete_camera(999)

        assert success is False

    # Detection Tests
    def test_create_detection(self, db_service, sample_camera):
        """Test creating a detection"""
        detection_data = DetectionCreate(
            camera_id=sample_camera.id,
            epis_detected={"helmet": True, "gloves": False},
            confidence=0.85,
            is_compliant=False,
            person_count=1
        )

        detection = db_service.create_detection(detection_data)

        assert detection is not None
        assert detection.id is not None
        assert detection.camera_id == sample_camera.id
        assert detection.is_compliant is False

    def test_get_detection(self, db_service, sample_camera):
        """Test retrieving a detection"""
        # Create detection first
        detection_data = DetectionCreate(
            camera_id=sample_camera.id,
            epis_detected={"helmet": True},
            confidence=0.9,
            is_compliant=True,
            person_count=1
        )
        created = db_service.create_detection(detection_data)

        # Retrieve detection
        detection = db_service.get_detection(created.id)

        assert detection is not None
        assert detection.id == created.id

    def test_get_detections_by_camera(self, db_service, sample_camera):
        """Test retrieving detections by camera"""
        # Create multiple detections
        for i in range(3):
            detection_data = DetectionCreate(
                camera_id=sample_camera.id,
                epis_detected={"helmet": True},
                confidence=0.8 + i * 0.05,
                is_compliant=True,
                person_count=1
            )
            db_service.create_detection(detection_data)

        detections = db_service.get_detections_by_camera(sample_camera.id)

        assert len(detections) == 3

    def test_get_recent_detections(self, db_service, sample_camera):
        """Test retrieving recent detections"""
        # Create detections
        for i in range(5):
            detection_data = DetectionCreate(
                camera_id=sample_camera.id,
                epis_detected={"helmet": True},
                confidence=0.8,
                is_compliant=True,
                person_count=1
            )
            db_service.create_detection(detection_data)

        detections = db_service.get_recent_detections(limit=3)

        assert len(detections) == 3

    def test_get_non_compliant_detections(self, db_service, sample_camera):
        """Test retrieving non-compliant detections"""
        # Create compliant detection
        detection_data1 = DetectionCreate(
            camera_id=sample_camera.id,
            epis_detected={"helmet": True},
            confidence=0.9,
            is_compliant=True,
            person_count=1
        )
        db_service.create_detection(detection_data1)

        # Create non-compliant detection
        detection_data2 = DetectionCreate(
            camera_id=sample_camera.id,
            epis_detected={"helmet": False},
            confidence=0.8,
            is_compliant=False,
            person_count=1
        )
        db_service.create_detection(detection_data2)

        non_compliant = db_service.get_non_compliant_detections()

        assert len(non_compliant) == 1
        assert non_compliant[0].is_compliant is False

    # Alert Tests
    def test_create_alert(self, db_service, sample_camera):
        """Test creating an alert"""
        # Create detection first
        detection_data = DetectionCreate(
            camera_id=sample_camera.id,
            epis_detected={"helmet": False},
            confidence=0.8,
            is_compliant=False,
            person_count=1
        )
        detection = db_service.create_detection(detection_data)

        # Create alert
        alert_data = AlertCreate(
            detection_id=detection.id,
            severity="high",
            message="Missing helmet"
        )

        alert = db_service.create_alert(alert_data)

        assert alert is not None
        assert alert.id is not None
        assert alert.severity == "high"
        assert alert.message == "Missing helmet"

    def test_get_alerts(self, db_service, sample_camera):
        """Test retrieving alerts"""
        # Create detection and alert
        detection_data = DetectionCreate(
            camera_id=sample_camera.id,
            epis_detected={"helmet": False},
            confidence=0.8,
            is_compliant=False,
            person_count=1
        )
        detection = db_service.create_detection(detection_data)

        alert_data = AlertCreate(
            detection_id=detection.id,
            severity="medium",
            message="Test alert"
        )
        db_service.create_alert(alert_data)

        alerts = db_service.get_alerts()

        assert len(alerts) == 1
        assert alerts[0].severity == "medium"

    def test_get_alerts_unresolved_only(self, db_service, sample_camera):
        """Test retrieving only unresolved alerts"""
        # Create detection
        detection_data = DetectionCreate(
            camera_id=sample_camera.id,
            epis_detected={"helmet": False},
            confidence=0.8,
            is_compliant=False,
            person_count=1
        )
        detection = db_service.create_detection(detection_data)

        # Create unresolved alert
        alert_data1 = AlertCreate(
            detection_id=detection.id,
            severity="high",
            message="Unresolved alert"
        )
        db_service.create_alert(alert_data1)

        # Create resolved alert
        alert_data2 = AlertCreate(
            detection_id=detection.id,
            severity="low",
            message="Resolved alert"
        )
        alert = db_service.create_alert(alert_data2)
        db_service.resolve_alert(alert.id)

        unresolved = db_service.get_alerts(unresolved_only=True)

        assert len(unresolved) == 1
        assert unresolved[0].severity == "high"

    def test_resolve_alert(self, db_service, sample_camera):
        """Test resolving an alert"""
        # Create detection and alert
        detection_data = DetectionCreate(
            camera_id=sample_camera.id,
            epis_detected={"helmet": False},
            confidence=0.8,
            is_compliant=False,
            person_count=1
        )
        detection = db_service.create_detection(detection_data)

        alert_data = AlertCreate(
            detection_id=detection.id,
            severity="high",
            message="Test alert"
        )
        alert = db_service.create_alert(alert_data)

        # Resolve alert
        resolved_alert = db_service.resolve_alert(alert.id)

        assert resolved_alert is not None
        assert resolved_alert.is_resolved is True
        assert resolved_alert.resolved_at is not None

    # Statistics Tests
    def test_get_compliance_stats(self, db_service, sample_camera):
        """Test getting compliance statistics"""
        # Create detections
        for i in range(10):
            detection_data = DetectionCreate(
                camera_id=sample_camera.id,
                epis_detected={"helmet": i % 2 == 0},
                confidence=0.8,
                is_compliant=i % 2 == 0,
                person_count=1
            )
            db_service.create_detection(detection_data)

        stats = db_service.get_compliance_stats()

        assert stats is not None
        assert stats.total_detections == 10
        assert stats.compliant_detections == 5
        assert stats.non_compliant_detections == 5
        assert stats.compliance_rate == 50.0

    def test_get_camera_stats(self, db_service):
        """Test getting camera statistics"""
        # Create cameras and detections
        for i in range(2):
            camera_data = CameraCreate(
                name=f"Camera {i}",
                location=f"Location {i}",
                rtsp_url=f"rtsp://test{i}",
                is_active=True
            )
            camera = db_service.create_camera(camera_data)

            # Add detections
            for j in range(5):
                detection_data = DetectionCreate(
                    camera_id=camera.id,
                    epis_detected={"helmet": True},
                    confidence=0.8,
                    is_compliant=True,
                    person_count=1
                )
                db_service.create_detection(detection_data)

        stats = db_service.get_camera_stats(days=7)

        assert len(stats) == 2
        assert all(s.total_detections == 5 for s in stats)

    def test_cleanup_old_detections(self, db_service, sample_camera):
        """Test cleaning up old detections"""
        # This test would require mocking datetime or setting specific timestamps
        # For now, just verify the method exists
        count = db_service.cleanup_old_detections(days=30)

        assert isinstance(count, int)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
