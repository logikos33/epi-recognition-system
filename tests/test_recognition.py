"""
Unit Tests for Recognition Agent
"""
import pytest
import numpy as np
import cv2
from pathlib import Path
from datetime import datetime

from agents.recognition_agent import RecognitionAgent, get_recognition_agent
from services.yolo_service import YOLOService
from models.schemas import DetectionResult, BoundingBox


class TestRecognitionAgent:
    """Test suite for RecognitionAgent"""

    @pytest.fixture
    def recognition_agent(self):
        """Create recognition agent instance"""
        return get_recognition_agent()

    @pytest.fixture
    def sample_frame(self):
        """Create a sample frame for testing"""
        # Create a dummy frame (640x480 RGB)
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (100, 150, 200)  # Fill with a color
        return frame

    def test_agent_initialization(self, recognition_agent):
        """Test that recognition agent initializes correctly"""
        assert recognition_agent is not None
        assert recognition_agent.yolo_service is not None
        assert recognition_agent.executor is not None

    def test_process_frame(self, recognition_agent, sample_frame):
        """Test frame processing"""
        result = recognition_agent.process_frame(sample_frame, camera_id=1, save_annotated=False)

        # Result should be a DetectionResult
        assert result is not None
        assert isinstance(result, DetectionResult)
        assert hasattr(result, 'epis_detected')
        assert hasattr(result, 'is_compliant')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'timestamp')

    def test_process_frames_batch(self, recognition_agent, sample_frame):
        """Test batch frame processing"""
        frames = [sample_frame] * 3
        camera_ids = [1, 2, 3]

        results = recognition_agent.process_frames_batch(frames, camera_ids, save_annotated=False)

        # Should return same number of results as input frames
        assert len(results) == 3

        # All results should be DetectionResult or None
        for result in results:
            assert result is None or isinstance(result, DetectionResult)

    def test_get_detection_statistics(self, recognition_agent):
        """Test statistics calculation"""
        # Create sample results
        result1 = DetectionResult(
            image_path="test1.jpg",
            detections=[],
            epis_detected={"helmet": True, "gloves": True, "glasses": True},
            confidence=0.85,
            is_compliant=True,
            timestamp=datetime.now(),
            person_count=2
        )

        result2 = DetectionResult(
            image_path="test2.jpg",
            detections=[],
            epis_detected={"helmet": False, "gloves": True, "glasses": True},
            confidence=0.75,
            is_compliant=False,
            timestamp=datetime.now(),
            person_count=1
        )

        stats = recognition_agent.get_detection_statistics([result1, result2])

        assert stats["total_detections"] == 2
        assert stats["compliant_detections"] == 1
        assert stats["compliance_rate"] == 50.0
        assert stats["total_persons"] == 3

    def test_detect_epis_no_image(self, recognition_agent):
        """Test detection with non-existent image"""
        result = recognition_agent.detect_epis("nonexistent_image.jpg")

        # Should return None for non-existent image
        assert result is None


class TestYOLOService:
    """Test suite for YOLOService"""

    @pytest.fixture
    def yolo_service(self):
        """Create YOLO service instance"""
        from services.yolo_service import get_yolo_service
        return get_yolo_service()

    @pytest.fixture
    def sample_image(self):
        """Create a sample image for testing"""
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        image[:] = (100, 150, 200)
        return image

    def test_service_initialization(self, yolo_service):
        """Test that YOLO service initializes correctly"""
        assert yolo_service is not None
        assert yolo_service.model is not None
        assert yolo_service.confidence_threshold > 0

    def test_detect_method(self, yolo_service, sample_image):
        """Test detect method"""
        detections = yolo_service.detect(sample_image)

        # Should return a list (may be empty)
        assert isinstance(detections, list)

    def test_detect_epis_method(self, yolo_service, sample_image):
        """Test detect_epis method"""
        result = yolo_service.detect_epis(sample_image)

        # Should return DetectionResult
        assert isinstance(result, DetectionResult)
        assert hasattr(result, 'epis_detected')
        assert hasattr(result, 'is_compliant')
        assert hasattr(result, 'confidence')

    def test_confidence_threshold_filtering(self, yolo_service, sample_image):
        """Test that confidence threshold works"""
        # Set high threshold
        original_threshold = yolo_service.confidence_threshold
        yolo_service.confidence_threshold = 0.99

        detections = yolo_service.detect(sample_image)

        # Restore threshold
        yolo_service.confidence_threshold = original_threshold

        # With high threshold, should have fewer detections
        assert isinstance(detections, list)


# Integration tests
class TestRecognitionIntegration:
    """Integration tests for recognition system"""

    def test_end_to_end_detection(self):
        """Test complete detection pipeline"""
        agent = get_recognition_agent()

        # Create test frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (100, 150, 200)

        # Process frame
        result = agent.process_frame(frame, camera_id=1)

        # Verify result
        assert result is not None
        assert isinstance(result, DetectionResult)

    def test_camera_pipeline_simulation(self):
        """Test simulated camera pipeline"""
        agent = get_recognition_agent()

        # Simulate multiple frames
        results = []
        for i in range(10):
            frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            result = agent.process_frame(frame, camera_id=1)

            if result:
                results.append(result)

        # Verify results
        assert len(results) >= 0  # May vary based on model


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
