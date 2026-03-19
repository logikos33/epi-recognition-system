"""
Recognition Agent - EPI Detection using YOLO
"""
import cv2
import numpy as np
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor

from services.yolo_service import YOLOService, get_yolo_service
from models.schemas import BoundingBox, DetectionResult
from utils.logger import get_logger
from utils.config import get_config


class RecognitionAgent:
    """
    Agent responsible for detecting EPIs in images using YOLO
    """

    def __init__(
        self,
        yolo_service: Optional[YOLOService] = None,
        confidence_threshold: Optional[float] = None
    ):
        """
        Initialize recognition agent

        Args:
            yolo_service: YOLO service instance
            confidence_threshold: Detection confidence threshold
        """
        self.logger = get_logger(__name__)
        self.config = get_config()

        # Initialize YOLO service
        self.yolo_service = yolo_service or get_yolo_service()

        if confidence_threshold:
            self.yolo_service.confidence_threshold = confidence_threshold

        # Thread pool for parallel processing
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_processing_threads)

        self.logger.info("Recognition Agent initialized")

    def process_frame(
        self,
        frame: np.ndarray,
        camera_id: int,
        save_annotated: bool = False
    ) -> Optional[DetectionResult]:
        """
        Process a single frame for EPI detection

        Args:
            frame: Input frame
            camera_id: Camera ID
            save_annotated: Whether to save annotated image

        Returns:
            DetectionResult or None if processing fails
        """
        try:
            # Detect EPIs using YOLO service
            result = self.yolo_service.detect_epis(frame)

            # Add camera ID to result
            result.image_path = f"camera_{camera_id}_{result.timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"

            # Save annotated image if requested
            if save_annotated:
                self._save_annotated_frame(frame, result, camera_id)

            self.logger.debug(
                f"Processed frame from camera {camera_id}: "
                f"compliant={result.is_compliant}, persons={result.person_count}"
            )

            return result

        except Exception as e:
            self.logger.error(f"Error processing frame from camera {camera_id}: {e}")
            return None

    def process_frames_batch(
        self,
        frames: List[np.ndarray],
        camera_ids: List[int],
        save_annotated: bool = False
    ) -> List[Optional[DetectionResult]]:
        """
        Process multiple frames in batch

        Args:
            frames: List of input frames
            camera_ids: List of camera IDs
            save_annotated: Whether to save annotated images

        Returns:
            List of detection results
        """
        if len(frames) != len(camera_ids):
            self.logger.error("Number of frames must match number of camera IDs")
            return []

        results = []

        # Process frames in parallel using thread pool
        futures = []
        for frame, camera_id in zip(frames, camera_ids):
            future = self.executor.submit(self.process_frame, frame, camera_id, save_annotated)
            futures.append(future)

        # Collect results
        for future in futures:
            try:
                result = future.result(timeout=10)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Error in batch processing: {e}")
                results.append(None)

        return results

    async def process_frame_async(
        self,
        frame: np.ndarray,
        camera_id: int,
        save_annotated: bool = False
    ) -> Optional[DetectionResult]:
        """
        Process frame asynchronously

        Args:
            frame: Input frame
            camera_id: Camera ID
            save_annotated: Whether to save annotated image

        Returns:
            DetectionResult or None
        """
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self.process_frame,
            frame,
            camera_id,
            save_annotated
        )
        return result

    def detect_epis(
        self,
        image_path: str,
        save_annotated: bool = True
    ) -> Optional[DetectionResult]:
        """
        Detect EPIs in an image file

        Args:
            image_path: Path to image file
            save_annotated: Whether to save annotated image

        Returns:
            DetectionResult or None
        """
        try:
            # Read image
            image = cv2.imread(image_path)

            if image is None:
                self.logger.error(f"Failed to read image: {image_path}")
                return None

            # Process image
            result = self.process_frame(image, camera_id=0, save_annotated=save_annotated)

            # Update image path
            if result:
                result.image_path = image_path

            return result

        except Exception as e:
            self.logger.error(f"Error detecting EPIs in image {image_path}: {e}")
            return None

    def detect_epis_in_video(
        self,
        video_path: str,
        frame_interval: int = 30,
        output_path: Optional[str] = None
    ) -> List[DetectionResult]:
        """
        Detect EPIs in a video file

        Args:
            video_path: Path to video file
            frame_interval: Process every Nth frame
            output_path: Path to save annotated video (optional)

        Returns:
            List of detection results
        """
        self.logger.info(f"Processing video: {video_path}")

        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            self.logger.error(f"Failed to open video: {video_path}")
            return []

        # Get video properties
        fps = int(cap.get(cv2.CAP_PROP_FPS))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # Setup video writer if output path specified
        video_writer = None
        if output_path:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            video_writer = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        results = []
        frame_count = 0
        processed_count = 0

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            frame_count += 1

            # Process frame at interval
            if frame_count % frame_interval == 0:
                result = self.process_frame(frame, camera_id=0, save_annotated=False)

                if result:
                    results.append(result)
                    processed_count += 1

                    # Write annotated frame to output video
                    if video_writer:
                        annotated = self._create_annotated_frame(frame, result)
                        video_writer.write(annotated)

                # Log progress
                if processed_count % 10 == 0:
                    self.logger.info(f"Processed {processed_count} frames from {video_path}")

        # Clean up
        cap.release()
        if video_writer:
            video_writer.release()

        self.logger.info(f"Processed {processed_count} frames from {video_path}")
        return results

    def _save_annotated_frame(
        self,
        frame: np.ndarray,
        result: DetectionResult,
        camera_id: int
    ):
        """
        Save annotated frame to disk

        Args:
            frame: Original frame
            result: Detection result
            camera_id: Camera ID
        """
        try:
            # Create annotated frame
            annotated = self._create_annotated_frame(frame, result)

            # Generate filename
            filename = f"camera_{camera_id}_{result.timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            filepath = self.config.annotated_images_dir / filename

            # Save image
            cv2.imwrite(str(filepath), annotated)

            self.logger.debug(f"Saved annotated frame: {filepath}")

        except Exception as e:
            self.logger.error(f"Error saving annotated frame: {e}")

    def _create_annotated_frame(
        self,
        frame: np.ndarray,
        result: DetectionResult
    ) -> np.ndarray:
        """
        Create annotated frame with bounding boxes and information

        Args:
            frame: Original frame
            result: Detection result

        Returns:
            Annotated frame
        """
        annotated = frame.copy()

        # Draw bounding boxes
        for bbox in result.detections:
            x1, y1, x2, y2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)

            # Choose color based on class
            color = self._get_color_for_class(bbox.class_name)

            # Draw rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Add label
            label = f"{bbox.class_name}: {bbox.confidence:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)

            # Draw label background
            cv2.rectangle(
                annotated,
                (x1, y1 - label_size[1] - 10),
                (x1 + label_size[0], y1),
                color,
                -1
            )

            # Draw label text
            cv2.putText(
                annotated,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                2
            )

        # Add compliance status
        status_text = "COMPLIANT" if result.is_compliant else "NON-COMPLIANT"
        status_color = (0, 255, 0) if result.is_compliant else (0, 0, 255)

        # Draw status background
        cv2.rectangle(
            annotated,
            (10, 10),
            (300, 80),
            (0, 0, 0),
            -1
        )

        # Draw status text
        cv2.putText(
            annotated,
            f"Status: {status_text}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            status_color,
            2
        )

        # Draw timestamp
        cv2.putText(
            annotated,
            f"Time: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            (20, 65),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )

        # Draw EPI status
        y_offset = 100
        for epi_type, detected in result.epis_detected.items():
            epi_status = "✓" if detected else "✗"
            epi_color = (0, 255, 0) if detected else (0, 0, 255)

            cv2.putText(
                annotated,
                f"{epi_status} {epi_type}",
                (20, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                epi_color,
                2
            )

            y_offset += 25

        return annotated

    def _get_color_for_class(self, class_name: str) -> tuple:
        """
        Get color for class bounding box

        Args:
            class_name: Class name

        Returns:
            BGR color tuple
        """
        class_lower = class_name.lower()

        # EPI classes - green
        if any(epi in class_lower for epi in ['helmet', 'glove', 'glass', 'vest', 'boot']):
            return (0, 255, 0)

        # Person - blue
        if class_lower == 'person':
            return (255, 0, 0)

        # Default - red
        return (0, 0, 255)

    def get_detection_statistics(self, results: List[DetectionResult]) -> Dict[str, Any]:
        """
        Calculate statistics from detection results

        Args:
            results: List of detection results

        Returns:
            Statistics dictionary
        """
        if not results:
            return {
                "total_detections": 0,
                "compliant_detections": 0,
                "compliance_rate": 0.0,
                "total_persons": 0,
                "epi_detection_rates": {}
            }

        total = len(results)
        compliant = sum(1 for r in results if r.is_compliant)
        total_persons = sum(r.person_count for r in results)

        compliance_rate = (compliant / total * 100) if total > 0 else 0

        # Calculate EPI detection rates
        epi_counts = {}
        for result in results:
            for epi_type, detected in result.epis_detected.items():
                if epi_type not in epi_counts:
                    epi_counts[epi_type] = {"detected": 0, "total": 0}
                epi_counts[epi_type]["total"] += 1
                if detected:
                    epi_counts[epi_type]["detected"] += 1

        epi_detection_rates = {}
        for epi_type, counts in epi_counts.items():
            rate = (counts["detected"] / counts["total"] * 100) if counts["total"] > 0 else 0
            epi_detection_rates[epi_type] = round(rate, 2)

        return {
            "total_detections": total,
            "compliant_detections": compliant,
            "compliance_rate": round(compliance_rate, 2),
            "total_persons": total_persons,
            "epi_detection_rates": epi_detection_rates
        }

    def load_model(self, model_path: str):
        """
        Load a custom YOLO model

        Args:
            model_path: Path to model file
        """
        self.logger.info(f"Loading custom model: {model_path}")
        self.yolo_service.load_custom_model(model_path)

    def shutdown(self):
        """
        Shutdown the recognition agent
        """
        self.logger.info("Shutting down recognition agent")
        self.executor.shutdown(wait=True)


def get_recognition_agent() -> RecognitionAgent:
    """
    Get or create recognition agent instance

    Returns:
        RecognitionAgent: Recognition agent instance
    """
    return RecognitionAgent()


# CLI support for standalone execution
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="EPI Recognition Agent")
    parser.add_argument("--image", type=str, help="Path to image file")
    parser.add_argument("--video", type=str, help="Path to video file")
    parser.add_argument("--camera", type=int, help="Camera ID for webcam")
    parser.add_argument("--duration", type=int, default=10, help="Duration in seconds for webcam")
    parser.add_argument("--confidence", type=float, default=0.5, help="Confidence threshold")
    parser.add_argument("--output", type=str, help="Output path for annotated results")

    args = parser.parse_args()

    agent = get_recognition_agent()

    if args.image:
        result = agent.detect_epis(args.image, save_annotated=True)

        if result:
            print(f"Detection Result:")
            print(f"  Compliant: {result.is_compliant}")
            print(f"  Persons: {result.person_count}")
            print(f"  EPIs Detected: {result.epis_detected}")
            print(f"  Confidence: {result.confidence:.2f}")

    elif args.video:
        output_path = args.output or "output_annotated.mp4"
        results = agent.detect_epis_in_video(args.video, output_path=output_path)

        stats = agent.get_detection_statistics(results)
        print(f"Video Processing Results:")
        print(f"  Total Detections: {stats['total_detections']}")
        print(f"  Compliance Rate: {stats['compliance_rate']:.2f}%")

    elif args.camera is not None:
        print(f"Capturing from camera {args.camera} for {args.duration} seconds...")
        from services.camera_service import get_camera_service

        camera_service = get_camera_service()

        def frame_callback(frame):
            result = agent.process_frame(frame, camera_id=args.camera, save_annotated=False)
            if result:
                print(f"Frame: Compliant={result.is_compliant}, Persons={result.person_count}")

        camera_service.capture_from_webcam(args.camera, args.duration, frame_callback)

    else:
        print("Please specify --image, --video, or --camera")
