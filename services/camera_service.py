"""
Camera Service - Video Capture from Multiple Sources
"""
import cv2
import numpy as np
from threading import Thread, Lock
from typing import Optional, Dict, List, Callable
from queue import Queue
from pathlib import Path
import time

from utils.logger import get_logger
from utils.config import get_config


class CameraSource:
    """
    Represents a camera source (RTSP, webcam, file)
    """

    def __init__(
        self,
        camera_id: int,
        source_url: str,
        name: str = "",
        location: str = ""
    ):
        """
        Initialize camera source

        Args:
            camera_id: Unique camera identifier
            source_url: URL or path to video source
            name: Camera name
            location: Camera location
        """
        self.camera_id = camera_id
        self.source_url = source_url
        self.name = name
        self.location = location
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_running = False

    def __repr__(self):
        return f"<CameraSource(id={self.camera_id}, name='{self.name}', url='{self.source_url}')>"


class CameraService:
    """
    Service for managing multiple camera sources and capturing frames
    """

    def __init__(self, max_cameras: Optional[int] = None):
        """
        Initialize camera service

        Args:
            max_cameras: Maximum number of cameras to support
        """
        self.logger = get_logger(__name__)
        self.config = get_config()

        self.max_cameras = max_cameras or self.config.max_cameras

        # Camera management
        self.cameras: Dict[int, CameraSource] = {}
        self.camera_threads: Dict[int, Thread] = {}
        self.frame_queues: Dict[int, Queue] = {}
        self.locks: Dict[int, Lock] = {}

        # Callbacks for new frames
        self.frame_callbacks: Dict[int, List[Callable]] = {}

        # Service state
        self.is_running = False

    def add_camera(
        self,
        camera_id: int,
        source_url: str,
        name: str = "",
        location: str = ""
    ) -> bool:
        """
        Add a camera to the service

        Args:
            camera_id: Unique camera identifier
            source_url: URL or path to video source
            name: Camera name
            location: Camera location

        Returns:
            True if added successfully
        """
        if camera_id in self.cameras:
            self.logger.warning(f"Camera {camera_id} already exists")
            return False

        if len(self.cameras) >= self.max_cameras:
            self.logger.error(f"Maximum number of cameras ({self.max_cameras}) reached")
            return False

        # Create camera source
        camera = CameraSource(camera_id, source_url, name, location)
        self.cameras[camera_id] = camera

        # Initialize frame queue and lock
        self.frame_queues[camera_id] = Queue(maxsize=10)
        self.locks[camera_id] = Lock()
        self.frame_callbacks[camera_id] = []

        self.logger.info(f"Added camera: {camera}")
        return True

    def remove_camera(self, camera_id: int) -> bool:
        """
        Remove a camera from the service

        Args:
            camera_id: Camera ID to remove

        Returns:
            True if removed successfully
        """
        if camera_id not in self.cameras:
            self.logger.warning(f"Camera {camera_id} not found")
            return False

        # Stop camera if running
        if self.cameras[camera_id].is_running:
            self.stop_camera(camera_id)

        # Clean up
        del self.cameras[camera_id]

        if camera_id in self.frame_queues:
            del self.frame_queues[camera_id]

        if camera_id in self.locks:
            del self.locks[camera_id]

        if camera_id in self.frame_callbacks:
            del self.frame_callbacks[camera_id]

        self.logger.info(f"Removed camera {camera_id}")
        return True

    def start_camera(self, camera_id: int) -> bool:
        """
        Start capturing from a camera

        Args:
            camera_id: Camera ID to start

        Returns:
            True if started successfully
        """
        if camera_id not in self.cameras:
            self.logger.error(f"Camera {camera_id} not found")
            return False

        if self.cameras[camera_id].is_running:
            self.logger.warning(f"Camera {camera_id} is already running")
            return True

        # Create capture thread
        thread = Thread(
            target=self._capture_loop,
            args=(camera_id,),
            daemon=True
        )

        self.camera_threads[camera_id] = thread
        thread.start()

        self.logger.info(f"Started camera {camera_id}")
        return True

    def stop_camera(self, camera_id: int) -> bool:
        """
        Stop capturing from a camera

        Args:
            camera_id: Camera ID to stop

        Returns:
            True if stopped successfully
        """
        if camera_id not in self.cameras:
            self.logger.warning(f"Camera {camera_id} not found")
            return False

        camera = self.cameras[camera_id]
        camera.is_running = False

        # Wait for thread to finish
        if camera_id in self.camera_threads:
            thread = self.camera_threads[camera_id]
            if thread.is_alive():
                thread.join(timeout=5)
            del self.camera_threads[camera_id]

        self.logger.info(f"Stopped camera {camera_id}")
        return True

    def start_all_cameras(self) -> bool:
        """
        Start all cameras

        Returns:
            True if all started successfully
        """
        success = True
        for camera_id in self.cameras:
            if not self.start_camera(camera_id):
                success = False
        return success

    def stop_all_cameras(self) -> bool:
        """
        Stop all cameras

        Returns:
            True if all stopped successfully
        """
        success = True
        for camera_id in list(self.cameras.keys()):
            if not self.stop_camera(camera_id):
                success = False
        return success

    def _capture_loop(self, camera_id: int):
        """
        Main capture loop for a camera (runs in separate thread)

        Args:
            camera_id: Camera ID
        """
        camera = self.cameras[camera_id]

        # Open video capture
        cap = cv2.VideoCapture(camera.source_url)

        if not cap.isOpened():
            self.logger.error(f"Failed to open camera {camera_id}: {camera.source_url}")
            return

        camera.cap = cap
        camera.is_running = True

        self.logger.info(f"Capture loop started for camera {camera_id}")

        frame_count = 0
        interval = self.config.frame_extraction_interval

        while camera.is_running:
            try:
                ret, frame = cap.read()

                if not ret:
                    self.logger.warning(f"Failed to read frame from camera {camera_id}")
                    # Try to reconnect
                    time.sleep(1)
                    cap.open(camera.source_url)
                    continue

                frame_count += 1

                # Extract frame at specified interval
                if frame_count % (interval * int(cap.get(cv2.CAP_PROP_FPS)) or 1) == 0:
                    # Add to queue (non-blocking)
                    if not self.frame_queues[camera_id].full():
                        timestamp = time.time()
                        self.frame_queues[camera_id].put((frame, timestamp))

                    # Trigger callbacks
                    self._trigger_callbacks(camera_id, frame, timestamp)

                # Small sleep to prevent CPU overload
                time.sleep(0.01)

            except Exception as e:
                self.logger.error(f"Error in capture loop for camera {camera_id}: {e}")
                camera.is_running = False

        # Clean up
        cap.release()
        camera.cap = None
        self.logger.info(f"Capture loop stopped for camera {camera_id}")

    def get_frame(self, camera_id: int, timeout: float = 1.0) -> Optional[tuple]:
        """
        Get the latest frame from a camera

        Args:
            camera_id: Camera ID
            timeout: Timeout in seconds

        Returns:
            Tuple of (frame, timestamp) or None
        """
        if camera_id not in self.frame_queues:
            return None

        try:
            return self.frame_queues[camera_id].get(timeout=timeout)
        except:
            return None

    def get_latest_frames(self) -> Dict[int, np.ndarray]:
        """
        Get the latest frame from all cameras

        Returns:
            Dictionary mapping camera_id to frame
        """
        frames = {}

        for camera_id in self.cameras:
            frame_data = self.get_frame(camera_id, timeout=0.1)
            if frame_data:
                frames[camera_id] = frame_data[0]

        return frames

    def add_frame_callback(self, camera_id: int, callback: Callable[[np.ndarray, float], None]):
        """
        Add a callback function to be called when a new frame is available

        Args:
            camera_id: Camera ID
            callback: Callback function that receives (frame, timestamp)
        """
        if camera_id in self.frame_callbacks:
            self.frame_callbacks[camera_id].append(callback)

    def _trigger_callbacks(self, camera_id: int, frame: np.ndarray, timestamp: float):
        """
        Trigger all callbacks for a camera

        Args:
            camera_id: Camera ID
            frame: Frame data
            timestamp: Frame timestamp
        """
        if camera_id in self.frame_callbacks:
            for callback in self.frame_callbacks[camera_id]:
                try:
                    callback(frame, timestamp)
                except Exception as e:
                    self.logger.error(f"Error in frame callback for camera {camera_id}: {e}")

    def get_camera_info(self, camera_id: int) -> Optional[Dict]:
        """
        Get information about a camera

        Args:
            camera_id: Camera ID

        Returns:
            Camera information dictionary or None
        """
        if camera_id not in self.cameras:
            return None

        camera = self.cameras[camera_id]

        # Get video properties if available
        width = height = fps = 0
        if camera.cap and camera.cap.isOpened():
            width = int(camera.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(camera.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = int(camera.cap.get(cv2.CAP_PROP_FPS))

        return {
            "camera_id": camera.camera_id,
            "name": camera.name,
            "location": camera.location,
            "source_url": camera.source_url,
            "is_running": camera.is_running,
            "width": width,
            "height": height,
            "fps": fps
        }

    def get_all_cameras_info(self) -> List[Dict]:
        """
        Get information about all cameras

        Returns:
            List of camera information dictionaries
        """
        return [
            self.get_camera_info(camera_id)
            for camera_id in self.cameras
        ]

    def capture_from_file(
        self,
        file_path: str,
        callback: Callable[[np.ndarray], None],
        frame_interval: int = 1
    ) -> int:
        """
        Capture frames from a video file

        Args:
            file_path: Path to video file
            callback: Callback function for each frame
            frame_interval: Process every Nth frame

        Returns:
            Number of frames processed
        """
        self.logger.info(f"Capturing from file: {file_path}")

        cap = cv2.VideoCapture(file_path)

        if not cap.isOpened():
            self.logger.error(f"Failed to open video file: {file_path}")
            return 0

        frame_count = 0
        processed_count = 0

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            frame_count += 1

            # Process frame at interval
            if frame_count % frame_interval == 0:
                try:
                    callback(frame)
                    processed_count += 1
                except Exception as e:
                    self.logger.error(f"Error processing frame {frame_count}: {e}")

        cap.release()
        self.logger.info(f"Processed {processed_count} frames from {file_path}")

        return processed_count

    def capture_from_webcam(
        self,
        webcam_id: int = 0,
        duration: int = 10,
        callback: Callable[[np.ndarray], None] = None
    ) -> int:
        """
        Capture frames from webcam

        Args:
            webcam_id: Webcam device ID
            duration: Duration in seconds
            callback: Callback function for each frame

        Returns:
            Number of frames captured
        """
        self.logger.info(f"Capturing from webcam {webcam_id} for {duration} seconds")

        cap = cv2.VideoCapture(webcam_id)

        if not cap.isOpened():
            self.logger.error(f"Failed to open webcam {webcam_id}")
            return 0

        start_time = time.time()
        frame_count = 0

        while True:
            ret, frame = cap.read()

            if not ret:
                break

            frame_count += 1

            if callback:
                try:
                    callback(frame)
                except Exception as e:
                    self.logger.error(f"Error in webcam callback: {e}")

            # Check duration
            if time.time() - start_time >= duration:
                break

            # Display frame (optional)
            cv2.imshow('Webcam', frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

        cap.release()
        cv2.destroyAllWindows()

        self.logger.info(f"Captured {frame_count} frames from webcam")
        return frame_count

    def release_all(self):
        """
        Release all camera resources
        """
        self.stop_all_cameras()

        for camera_id in list(self.cameras.keys()):
            self.remove_camera(camera_id)

        self.logger.info("Released all camera resources")


def get_camera_service() -> CameraService:
    """
    Get or create camera service instance

    Returns:
        CameraService: Camera service instance
    """
    return CameraService()
