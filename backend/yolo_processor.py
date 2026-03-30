"""
YOLO Processor for Real-time Object Detection

Runs continuous YOLO detection on RTSP streams in background threads.
Emits detection results via callback functions for WebSocket broadcasting.
"""
import threading
import time
import cv2
import logging
from typing import Callable, Optional, Dict, Any, List
import numpy as np

logger = logging.getLogger(__name__)


class YOLOProcessor(threading.Thread):
    """
    Thread-based continuous YOLO detection for camera streams.

    Captures frames from RTSP URL at specified FPS, runs YOLO detection,
    and sends results via callback for WebSocket broadcasting.
    """

    def __init__(
        self,
        camera_id: int,
        rtsp_url: str,
        model,
        fps: int = 5,
        detection_callback: Optional[Callable[[Dict[str, Any]], None]] = None,
        stop_event: Optional[threading.Event] = None
    ):
        """
        Initialize YOLO processor thread.

        Args:
            camera_id: Camera identifier
            rtsp_url: RTSP stream URL
            model: YOLO model instance
            fps: Target detection FPS (default 5)
            detection_callback: Callback function for detection results
            stop_event: Threading event to signal stop
        """
        super().__init__(daemon=True)
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.model = model
        self.fps = fps
        self.detection_callback = detection_callback
        self.stop_event = stop_event or threading.Event()
        self.cap = None
        self.frame_count = 0
        self.detection_count = 0

        logger.info(f"🎯 YOLOProcessor initialized for camera {camera_id} at {fps} FPS")

    def run(self):
        """
        Main detection loop.

        Captures frames from RTSP stream at target FPS,
        runs YOLO inference, and sends results via callback.
        """
        logger.info(f"🚀 Starting YOLO detection for camera {self.camera_id}")

        # Open RTSP stream with OpenCV
        self.cap = cv2.VideoCapture(self.rtsp_url)
        self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency

        if not self.cap.isOpened():
            logger.error(f"❌ Failed to open RTSP stream: {self.rtsp_url}")
            if self.detection_callback:
                self.detection_callback({
                    'camera_id': self.camera_id,
                    'status': 'error',
                    'error': 'Failed to open RTSP stream'
                })
            return

        # Calculate frame interval
        frame_interval = 1.0 / self.fps
        last_time = time.time()

        try:
            while not self.stop_event.is_set():
                current_time = time.time()
                elapsed = current_time - last_time

                # Throttle to target FPS
                if elapsed < frame_interval:
                    time.sleep(frame_interval - elapsed)
                    continue

                last_time = current_time

                # Read frame
                ret, frame = self.cap.read()
                if not ret:
                    logger.warning(f"⚠️ Failed to read frame from camera {self.camera_id}")
                    time.sleep(1)  # Wait before retry
                    continue

                self.frame_count += 1

                # Run YOLO detection
                try:
                    results = self.model.predict(
                        source=frame,
                        verbose=False,
                        conf=0.5,  # Confidence threshold
                        iou=0.45,  # NMS IOU threshold
                        max_det=100  # Max detections per frame
                    )

                    # Extract detection data
                    detections = self._extract_detections(results)

                    self.detection_count += len(detections)

                    # Send via callback if available
                    if self.detection_callback:
                        self.detection_callback({
                            'camera_id': self.camera_id,
                            'status': 'detecting',
                            'timestamp': time.time(),
                            'frame_number': self.frame_count,
                            'detections': detections
                        })

                except Exception as e:
                    logger.error(f"❌ YOLO detection error for camera {self.camera_id}: {e}")
                    if self.detection_callback:
                        self.detection_callback({
                            'camera_id': self.camera_id,
                            'status': 'error',
                            'error': str(e)
                        })
                    time.sleep(1)  # Brief pause before retry

        except Exception as e:
            logger.error(f"❌ Fatal error in YOLOProcessor for camera {self.camera_id}: {e}")
        finally:
            if self.cap:
                self.cap.release()
            logger.info(f"🛑 YOLOProcessor stopped for camera {self.camera_id}")
            logger.info(f"📊 Processed {self.frame_count} frames, {self.detection_count} detections")

    def _extract_detections(self, results) -> List[Dict[str, Any]]:
        """
        Extract detection data from YOLO results.

        Args:
            results: YOLO model results

        Returns:
            List of detection dictionaries
        """
        detections = []

        for result in results:
            for box in result.boxes:
                detection = {
                    'class_id': int(box.cls[0]),
                    'class_name': result.names[int(box.cls[0])],
                    'confidence': float(box.conf[0]),
                    'bbox': box.xyxy[0].tolist()  # [x1, y1, x2, y2]
                }
                detections.append(detection)

        return detections

    def stop(self):
        """
        Stop the detection thread gracefully.
        """
        logger.info(f"🛑 Stopping YOLOProcessor for camera {self.camera_id}")
        self.stop_event.set()

        # Wait for thread to finish (max 5 seconds)
        self.join(timeout=5.0)

        # Release capture if still open
        if self.cap:
            self.cap.release()


class YOLOProcessorManager:
    """
    Manages multiple YOLOProcessor threads.

    Starts, stops, and monitors YOLO detection threads for multiple cameras.
    """

    def __init__(self):
        """Initialize processor manager."""
        self.processors: Dict[int, YOLOProcessor] = {}
        self.detection_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.model = None
        logger.info("🎯 YOLOProcessorManager initialized")

    def set_model(self, model):
        """
        Set YOLO model for all processors.

        Args:
            model: YOLO model instance
        """
        self.model = model
        logger.info("✅ YOLO model set for processor manager")

    def set_detection_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """
        Set callback for detection results.

        Args:
            callback: Function to call with detection results
        """
        self.detection_callback = callback
        logger.info("✅ Detection callback registered")

    def start_processor(self, camera_id: int, rtsp_url: str, fps: int = 5) -> bool:
        """
        Start YOLO processor for a camera.

        Args:
            camera_id: Camera identifier
            rtsp_url: RTSP stream URL
            fps: Target detection FPS

        Returns:
            True if started successfully, False otherwise
        """
        if camera_id in self.processors:
            logger.warning(f"⚠️ Processor already running for camera {camera_id}")
            return False

        if not self.model:
            logger.error("❌ YOLO model not set")
            return False

        try:
            processor = YOLOProcessor(
                camera_id=camera_id,
                rtsp_url=rtsp_url,
                model=self.model,
                fps=fps,
                detection_callback=self.detection_callback
            )

            self.processors[camera_id] = processor
            processor.start()

            logger.info(f"✅ Started YOLO processor for camera {camera_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to start processor for camera {camera_id}: {e}")
            return False

    def stop_processor(self, camera_id: int) -> bool:
        """
        Stop YOLO processor for a camera.

        Args:
            camera_id: Camera identifier

        Returns:
            True if stopped successfully, False otherwise
        """
        if camera_id not in self.processors:
            logger.warning(f"⚠️ No processor running for camera {camera_id}")
            return False

        try:
            processor = self.processors[camera_id]
            processor.stop()
            del self.processors[camera_id]

            logger.info(f"✅ Stopped YOLO processor for camera {camera_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to stop processor for camera {camera_id}: {e}")
            return False

    def stop_all(self):
        """Stop all running processors."""
        logger.info(f"🛑 Stopping all {len(self.processors)} processors")

        for camera_id in list(self.processors.keys()):
            self.stop_processor(camera_id)

        logger.info("✅ All processors stopped")

    def get_active_cameras(self) -> List[int]:
        """
        Get list of cameras with active processors.

        Returns:
            List of camera IDs
        """
        return list(self.processors.keys())

    def is_processor_running(self, camera_id: int) -> bool:
        """
        Check if processor is running for a camera.

        Args:
            camera_id: Camera identifier

        Returns:
            True if running, False otherwise
        """
        if camera_id not in self.processors:
            return False

        processor = self.processors[camera_id]
        return processor.is_alive()
