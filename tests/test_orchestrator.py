"""
Integration Tests for Orchestrator Agent
"""
import pytest
import numpy as np
import time
from datetime import datetime
from pathlib import Path

from agents.orchestrator_agent import OrchestratorAgent, get_orchestrator_agent
from agents.recognition_agent import RecognitionAgent, get_recognition_agent
from agents.annotation_agent import AnnotationAgent, get_annotation_agent
from services.camera_service import CameraService, get_camera_service
from services.database_service import DatabaseService, get_database_service
from models.schemas import DetectionResult


class TestOrchestratorAgent:
    """Test suite for OrchestratorAgent"""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator instance"""
        return get_orchestrator_agent()

    @pytest.fixture
    def sample_frame(self):
        """Create a sample frame"""
        return np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

    def test_orchestrator_initialization(self, orchestrator):
        """Test that orchestrator initializes correctly"""
        assert orchestrator is not None
        assert orchestrator.recognition_agent is not None
        assert orchestrator.annotation_agent is not None
        assert orchestrator.camera_service is not None
        assert orchestrator.database_service is not None

    def test_get_system_status(self, orchestrator):
        """Test getting system status"""
        status = orchestrator.get_system_status()

        assert isinstance(status, dict)
        assert "is_running" in status
        assert "active_cameras" in status
        assert "total_cameras" in status
        assert "stats" in status

    def test_get_system_stats(self, orchestrator):
        """Test getting system statistics"""
        stats = orchestrator.get_system_stats()

        assert isinstance(stats, dict)
        assert "total_frames_processed" in stats
        assert "total_detections" in stats
        assert "non_compliant_detections" in stats
        assert "compliance_rate" in stats

    def test_add_camera(self, orchestrator):
        """Test adding a camera"""
        camera_id = orchestrator.add_camera(
            name="Test Camera",
            location="Test Location",
            rtsp_url="rtsp://test"
        )

        # Should return camera ID
        assert camera_id is not None
        assert isinstance(camera_id, int)

    def test_remove_camera(self, orchestrator):
        """Test removing a camera"""
        # Add a camera first
        camera_id = orchestrator.add_camera(
            name="Test Camera",
            location="Test Location",
            rtsp_url="rtsp://test"
        )

        # Remove the camera
        success = orchestrator.remove_camera(camera_id)

        assert success is True

    def test_process_pipeline(self, orchestrator, sample_frame):
        """Test processing pipeline"""
        # Process a single frame
        detection_id = orchestrator.process_single_frame(sample_frame, camera_id=1)

        # Detection ID may be None if no objects detected
        assert detection_id is None or isinstance(detection_id, int)

    def test_add_detection_callback(self, orchestrator, sample_frame):
        """Test detection callbacks"""
        callback_called = []

        def test_callback(result, camera_id):
            callback_called.append((result, camera_id))

        # Add callback
        orchestrator.add_detection_callback(test_callback)

        # Process a frame (this will trigger the callback internally)
        # Note: In real scenario, callback would be triggered during pipeline
        orchestrator.process_single_frame(sample_frame, camera_id=1)

        # Verify callback was added
        assert test_callback in orchestrator.detection_callbacks


class TestCameraIntegration:
    """Test camera service integration"""

    @pytest.fixture
    def camera_service(self):
        """Create camera service instance"""
        return get_camera_service()

    def test_add_camera(self, camera_service):
        """Test adding camera"""
        success = camera_service.add_camera(
            camera_id=1,
            source_url=0,  # Use webcam
            name="Test Webcam",
            location="Test"
        )

        assert success is True

    def test_remove_camera(self, camera_service):
        """Test removing camera"""
        camera_service.add_camera(
            camera_id=2,
            source_url=0,
            name="Test",
            location="Test"
        )

        success = camera_service.remove_camera(2)

        assert success is True

    def test_get_camera_info(self, camera_service):
        """Test getting camera information"""
        camera_service.add_camera(
            camera_id=3,
            source_url=0,
            name="Test Webcam",
            location="Test Location"
        )

        info = camera_service.get_camera_info(3)

        assert info is not None
        assert info["camera_id"] == 3
        assert info["name"] == "Test Webcam"


class TestDatabaseIntegration:
    """Test database service integration"""

    @pytest.fixture
    def database_service(self):
        """Create database service instance"""
        return get_database_service()

    def test_create_camera(self, database_service):
        """Test creating camera in database"""
        from models.schemas import CameraCreate

        camera_data = CameraCreate(
            name="Test Camera",
            location="Test Location",
            rtsp_url="rtsp://test",
            is_active=True
        )

        camera = database_service.create_camera(camera_data)

        assert camera is not None
        assert camera.id is not None
        assert camera.name == "Test Camera"

    def test_get_camera(self, database_service):
        """Test retrieving camera from database"""
        # Create camera first
        from models.schemas import CameraCreate

        camera_data = CameraCreate(
            name="Test Camera 2",
            location="Test Location 2",
            rtsp_url="rtsp://test2",
            is_active=True
        )

        created_camera = database_service.create_camera(camera_data)

        # Retrieve camera
        retrieved_camera = database_service.get_camera(created_camera.id)

        assert retrieved_camera is not None
        assert retrieved_camera.id == created_camera.id
        assert retrieved_camera.name == "Test Camera 2"

    def test_get_compliance_stats(self, database_service):
        """Test getting compliance statistics"""
        from datetime import datetime, timedelta

        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        stats = database_service.get_compliance_stats(start_date, end_date)

        assert stats is not None
        assert hasattr(stats, 'total_detections')
        assert hasattr(stats, 'compliance_rate')
        assert hasattr(stats, 'epi_detection_rates')


class TestEndToEndPipeline:
    """End-to-end integration tests"""

    def test_full_pipeline_simulation(self):
        """Test complete pipeline from frame to database"""
        orchestrator = get_orchestrator_agent()

        # Add test camera
        camera_id = orchestrator.add_camera(
            name="Test Camera",
            location="Test Location",
            rtsp_url="0"  # Webcam
        )

        assert camera_id is not None

        # Create test frame
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)

        # Process through pipeline
        detection_id = orchestrator.process_single_frame(frame, camera_id)

        # Verify (detection_id may be None if no objects detected)
        assert detection_id is None or isinstance(detection_id, int)

        # Cleanup
        orchestrator.remove_camera(camera_id)

    def test_multi_camera_simulation(self):
        """Test with multiple cameras"""
        orchestrator = get_orchestrator_agent()

        # Add multiple cameras
        camera_ids = []
        for i in range(3):
            camera_id = orchestrator.add_camera(
                name=f"Test Camera {i}",
                location=f"Location {i}",
                rtsp_url=str(i)
            )
            camera_ids.append(camera_id)

        assert len(camera_ids) == 3

        # Process frames from each camera
        for camera_id in camera_ids:
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            orchestrator.process_single_frame(frame, camera_id)

        # Check system stats
        stats = orchestrator.get_system_stats()
        assert "total_detections" in stats

        # Cleanup
        for camera_id in camera_ids:
            orchestrator.remove_camera(camera_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
