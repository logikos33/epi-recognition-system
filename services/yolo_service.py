"""
YOLO Service - Wrapper for Ultralytics YOLO Model
"""
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any
from ultralytics import YOLO
from PIL import Image

from utils.logger import get_logger
from utils.config import get_config
from models.schemas import BoundingBox, DetectionResult


class YOLOService:
    """
    Wrapper service for YOLO model operations
    """

    # Default class labels for COCO dataset (YOLO default)
    COCO_CLASSES = {
        0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 4: 'airplane',
        5: 'bus', 6: 'train', 7: 'truck', 8: 'boat', 9: 'traffic light',
        # ... more classes
    }

    # EPI-related classes (custom trained or mapped)
    EPI_CLASS_MAPPING = {
        'helmet': 'helmet',
        'hard hat': 'helmet',
        'gloves': 'gloves',
        'glasses': 'glasses',
        'sunglasses': 'glasses',
        'vest': 'vest',
        'safety vest': 'vest',
        'boots': 'boots'
    }

    def __init__(
        self,
        model_path: Optional[str] = None,
        confidence_threshold: Optional[float] = None,
        iou_threshold: Optional[float] = None
    ):
        """
        Initialize YOLO service

        Args:
            model_path: Path to YOLO model file
            confidence_threshold: Detection confidence threshold
            iou_threshold: IoU threshold for NMS
        """
        self.logger = get_logger(__name__)
        self.config = get_config()

        self.model_path = model_path or self.config.yolo_model_path
        self.confidence_threshold = confidence_threshold or self.config.detection_confidence_threshold
        self.iou_threshold = iou_threshold or self.config.iou_threshold

        self.model = None
        self._load_model()

    def _load_model(self):
        """
        Load YOLO model from file
        """
        try:
            self.logger.info(f"Loading YOLO model from: {self.model_path}")
            self.model = YOLO(self.model_path)
            self.logger.info("YOLO model loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to load YOLO model: {e}")
            raise

    def load_custom_model(self, model_path: str):
        """
        Load a custom YOLO model

        Args:
            model_path: Path to custom model file
        """
        self.model_path = model_path
        self._load_model()

    def detect(
        self,
        image: np.ndarray,
        save_annotated: bool = False,
        save_path: Optional[str] = None
    ) -> List[BoundingBox]:
        """
        Perform object detection on an image

        Args:
            image: Input image (numpy array)
            save_annotated: Whether to save annotated image
            save_path: Path to save annotated image

        Returns:
            List of BoundingBox objects
        """
        if self.model is None:
            raise ValueError("Model not loaded. Call load_model() first.")

        try:
            # Run inference
            results = self.model(
                image,
                conf=self.confidence_threshold,
                iou=self.iou_threshold,
                verbose=False
            )

            # Extract detections
            detections = []
            if results and len(results) > 0:
                result = results[0]

                # Get boxes
                boxes = result.boxes
                if boxes is not None:
                    for box in boxes:
                        # Get box coordinates
                        x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                        # Get confidence and class
                        confidence = float(box.conf[0].cpu().numpy())
                        class_id = int(box.cls[0].cpu().numpy())
                        class_name = result.names[class_id]

                        # Create bounding box object
                        bbox = BoundingBox(
                            x1=float(x1),
                            y1=float(y1),
                            x2=float(x2),
                            y2=float(y2),
                            confidence=confidence,
                            class_name=class_name
                        )
                        detections.append(bbox)

            # Save annotated image if requested
            if save_annotated and save_path:
                self._save_annotated_image(image, detections, save_path)

            return detections

        except Exception as e:
            self.logger.error(f"Error during detection: {e}")
            raise

    def detect_epis(
        self,
        image: np.ndarray,
        required_epis: Optional[Dict[str, bool]] = None
    ) -> DetectionResult:
        """
        Detect EPIs in an image and return detection result

        Args:
            image: Input image
            required_epis: Dictionary of required EPIs with their status

        Returns:
            DetectionResult object with EPI detection information
        """
        from datetime import datetime

        # Get required EPIs from config if not provided
        if required_epis is None:
            required_epis = self.config.epi_types

        # Perform detection
        detections = self.detect(image)

        # Analyze EPI detections
        epis_detected = {}
        person_count = 0

        for bbox in detections:
            class_name = bbox.class_name.lower()

            # Count persons
            if class_name == 'person':
                person_count += 1
                continue

            # Map detected class to EPI type
            epi_type = self._map_to_epi_type(class_name)
            if epi_type and epi_type in required_epis:
                epis_detected[epi_type] = True

        # Fill missing EPIs
        for epi_type in required_epis:
            if epi_type not in epis_detected:
                epis_detected[epi_type] = False

        # Calculate compliance
        is_compliant = self._check_compliance(epis_detected, required_epis)

        # Calculate overall confidence
        confidence = self._calculate_confidence(detections)

        # Create detection result
        result = DetectionResult(
            image_path="",  # Will be filled by caller
            detections=detections,
            epis_detected=epis_detected,
            confidence=confidence,
            is_compliant=is_compliant,
            timestamp=datetime.now(),
            person_count=person_count
        )

        return result

    def _map_to_epi_type(self, class_name: str) -> Optional[str]:
        """
        Map detected class name to EPI type

        Args:
            class_name: Detected class name

        Returns:
            EPI type or None if not an EPI
        """
        class_lower = class_name.lower()
        return self.EPI_CLASS_MAPPING.get(class_lower)

    def _check_compliance(
        self,
        epis_detected: Dict[str, bool],
        required_epis: Dict[str, bool]
    ) -> bool:
        """
        Check if detection is compliant with required EPIs

        Args:
            epis_detected: Detected EPIs
            required_epis: Required EPIs configuration

        Returns:
            True if compliant, False otherwise
        """
        for epi_type, is_detected in epis_detected.items():
            if required_epis.get(epi_type, {}).get('required', False) and not is_detected:
                return False
        return True

    def _calculate_confidence(self, detections: List[BoundingBox]) -> float:
        """
        Calculate average confidence from detections

        Args:
            detections: List of bounding box detections

        Returns:
            Average confidence
        """
        if not detections:
            return 0.0

        total_confidence = sum(d.confidence for d in detections)
        return total_confidence / len(detections)

    def _save_annotated_image(
        self,
        image: np.ndarray,
        detections: List[BoundingBox],
        save_path: str
    ):
        """
        Save image with annotated bounding boxes

        Args:
            image: Original image
            detections: List of detections
            save_path: Path to save annotated image
        """
        try:
            # Create a copy for annotation
            annotated = image.copy()

            # Draw bounding boxes
            for bbox in detections:
                # Convert to integer coordinates
                x1, y1, x2, y2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)

                # Choose color based on class
                color = self._get_color_for_class(bbox.class_name)

                # Draw rectangle
                cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

                # Add label
                label = f"{bbox.class_name}: {bbox.confidence:.2f}"
                label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
                cv2.rectangle(
                    annotated,
                    (x1, y1 - label_size[1] - 10),
                    (x1 + label_size[0], y1),
                    color,
                    -1
                )
                cv2.putText(
                    annotated,
                    label,
                    (x1, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 255),
                    2
                )

            # Save image
            cv2.imwrite(save_path, annotated)
            self.logger.debug(f"Saved annotated image to: {save_path}")

        except Exception as e:
            self.logger.error(f"Error saving annotated image: {e}")

    def _get_color_for_class(self, class_name: str) -> Tuple[int, int, int]:
        """
        Get color for class bounding box

        Args:
            class_name: Class name

        Returns:
            RGB color tuple
        """
        class_lower = class_name.lower()

        # EPI classes - green for detected
        if any(epi in class_lower for epi in ['helmet', 'glove', 'glass', 'vest', 'boot']):
            return (0, 255, 0)  # Green

        # Person - blue
        if class_lower == 'person':
            return (255, 0, 0)  # Blue

        # Default - red
        return (0, 0, 255)  # Red

    def process_frame(
        self,
        frame: np.ndarray,
        camera_id: int
    ) -> Optional[DetectionResult]:
        """
        Process a single frame from camera

        Args:
            frame: Video frame
            camera_id: Camera ID

        Returns:
            DetectionResult or None if processing fails
        """
        try:
            result = self.detect_epis(frame)

            # Add metadata
            result.image_path = f"camera_{camera_id}_{result.timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"

            return result

        except Exception as e:
            self.logger.error(f"Error processing frame: {e}")
            return None

    def batch_process(
        self,
        images: List[np.ndarray],
        batch_size: int = 8
    ) -> List[DetectionResult]:
        """
        Process multiple images in batch

        Args:
            images: List of images
            batch_size: Batch size for processing

        Returns:
            List of detection results
        """
        results = []

        for i in range(0, len(images), batch_size):
            batch = images[i:i + batch_size]

            for image in batch:
                try:
                    result = self.detect_epis(image)
                    results.append(result)
                except Exception as e:
                    self.logger.error(f"Error processing image in batch: {e}")

        return results


def get_yolo_service() -> YOLOService:
    """
    Get or create YOLO service instance

    Returns:
        YOLOService: YOLO service instance
    """
    return YOLOService()
