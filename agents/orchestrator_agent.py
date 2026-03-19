"""
Orchestrator Agent - Coordinates All Agents and Manages Data Flow
"""
import asyncio
import numpy as np
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime, timedelta
from threading import Thread, Event
import time
from queue import Queue

from agents.recognition_agent import RecognitionAgent, get_recognition_agent
from agents.annotation_agent import AnnotationAgent, get_annotation_agent
from agents.reporting_agent import ReportingAgent, get_reporting_agent
from services.camera_service import CameraService, get_camera_service
from services.database_service import DatabaseService, get_database_service
from models.schemas import DetectionResult
from utils.logger import get_logger
from utils.config import get_config


class OrchestratorAgent:
    """
    Orchestrator agent that coordinates all agents and manages the processing pipeline
    """

    def __init__(
        self,
        recognition_agent: Optional[RecognitionAgent] = None,
        annotation_agent: Optional[AnnotationAgent] = None,
        reporting_agent: Optional[ReportingAgent] = None,
        camera_service: Optional[CameraService] = None,
        database_service: Optional[DatabaseService] = None
    ):
        """
        Initialize orchestrator agent

        Args:
            recognition_agent: Recognition agent instance
            annotation_agent: Annotation agent instance
            reporting_agent: Reporting agent instance
            camera_service: Camera service instance
            database_service: Database service instance
        """
        self.logger = get_logger(__name__)
        self.config = get_config()

        # Initialize agents
        self.recognition_agent = recognition_agent or get_recognition_agent()
        self.annotation_agent = annotation_agent or get_annotation_agent()
        self.reporting_agent = reporting_agent or get_reporting_agent()
        self.camera_service = camera_service or get_camera_service()
        self.database_service = database_service or get_database_service()

        # Orchestration state
        self.is_running = False
        self.stop_event = Event()
        self.processing_threads: Dict[int, Thread] = {}
        self.frame_queues: Dict[int, Queue] = {}
        self.stats: Dict[str, Any] = {
            "total_frames_processed": 0,
            "total_detections": 0,
            "non_compliant_detections": 0,
            "start_time": None,
            "last_activity": None
        }

        # Callbacks for detection events
        self.detection_callbacks: List[Callable] = []

        self.logger.info("Orchestrator Agent initialized")

    def start_all_agents(self) -> bool:
        """
        Start all agents and services

        Returns:
            True if started successfully
        """
        try:
            self.logger.info("Starting all agents...")

            # Initialize cameras from database
            self._initialize_cameras()

            # Start all cameras
            self.camera_service.start_all_cameras()

            # Start processing threads for each camera
            for camera_id in self.camera_service.cameras:
                self._start_camera_processing(camera_id)

            self.is_running = True
            self.stats["start_time"] = datetime.now()

            self.logger.info("All agents started successfully")

            return True

        except Exception as e:
            self.logger.error(f"Error starting agents: {e}")
            return False

    def stop_all_agents(self) -> bool:
        """
        Stop all agents and services

        Returns:
            True if stopped successfully
        """
        try:
            self.logger.info("Stopping all agents...")

            self.is_running = False
            self.stop_event.set()

            # Stop camera processing threads
            for camera_id in list(self.processing_threads.keys()):
                self._stop_camera_processing(camera_id)

            # Stop all cameras
            self.camera_service.stop_all_cameras()

            # Shutdown recognition agent
            self.recognition_agent.shutdown()

            self.logger.info("All agents stopped successfully")

            return True

        except Exception as e:
            self.logger.error(f"Error stopping agents: {e}")
            return False

    def _initialize_cameras(self):
        """
        Initialize cameras from database configuration
        """
        try:
            cameras = self.database_service.get_all_cameras(active_only=True)

            for camera in cameras:
                self.camera_service.add_camera(
                    camera_id=camera.id,
                    source_url=camera.rtsp_url,
                    name=camera.name,
                    location=camera.location
                )

                self.logger.info(f"Initialized camera: {camera.name}")

        except Exception as e:
            self.logger.error(f"Error initializing cameras: {e}")

    def _start_camera_processing(self, camera_id: int):
        """
        Start processing thread for a camera

        Args:
            camera_id: Camera ID
        """
        if camera_id in self.processing_threads:
            self.logger.warning(f"Processing thread for camera {camera_id} already exists")
            return

        # Create frame queue
        self.frame_queues[camera_id] = Queue(maxsize=10)

        # Create processing thread
        thread = Thread(
            target=self._camera_processing_loop,
            args=(camera_id,),
            daemon=True
        )

        self.processing_threads[camera_id] = thread
        thread.start()

        self.logger.info(f"Started processing thread for camera {camera_id}")

    def _stop_camera_processing(self, camera_id: int):
        """
        Stop processing thread for a camera

        Args:
            camera_id: Camera ID
        """
        if camera_id not in self.processing_threads:
            return

        thread = self.processing_threads[camera_id]

        if thread.is_alive():
            thread.join(timeout=5)

        del self.processing_threads[camera_id]

        if camera_id in self.frame_queues:
            del self.frame_queues[camera_id]

        self.logger.info(f"Stopped processing thread for camera {camera_id}")

    def _camera_processing_loop(self, camera_id: int):
        """
        Main processing loop for a camera (runs in separate thread)

        Args:
            camera_id: Camera ID
        """
        self.logger.info(f"Camera processing loop started for camera {camera_id}")

        while self.is_running and not self.stop_event.is_set():
            try:
                # Get frame from camera
                frame_data = self.camera_service.get_frame(camera_id, timeout=1.0)

                if frame_data is None:
                    continue

                frame, timestamp = frame_data

                # Process frame through pipeline
                self._process_pipeline(frame, camera_id, timestamp)

                # Update stats
                self.stats["total_frames_processed"] += 1
                self.stats["last_activity"] = datetime.now()

            except Exception as e:
                self.logger.error(f"Error in camera processing loop for camera {camera_id}: {e}")

        self.logger.info(f"Camera processing loop stopped for camera {camera_id}")

    def _process_pipeline(self, frame: np.ndarray, camera_id: int, timestamp: float):
        """
        Process frame through the complete pipeline:
        Frame → Recognition → Annotation → Database → Reporting

        Args:
            frame: Video frame
            camera_id: Camera ID
            timestamp: Frame timestamp
        """
        try:
            # Step 1: Recognition - Detect EPIs
            detection_result = self.recognition_agent.process_frame(
                frame,
                camera_id,
                save_annotated=False
            )

            if detection_result is None:
                self.logger.warning(f"Recognition failed for camera {camera_id}")
                return

            # Step 2: Annotation - Enrich and save
            detection_id = self.annotation_agent.process_and_save(
                detection_result,
                camera_id,
                save_frame=True
            )

            if detection_id is None:
                self.logger.warning(f"Annotation failed for camera {camera_id}")
                return

            # Step 3: Update stats
            self.stats["total_detections"] += 1

            if not detection_result.is_compliant:
                self.stats["non_compliant_detections"] += 1

            # Step 4: Reporting - Update dashboard
            if self.reporting_agent:
                self.reporting_agent.update_detection(detection_result)

            # Step 5: Trigger callbacks
            self._trigger_detection_callbacks(detection_result, camera_id)

            self.logger.debug(
                f"Pipeline completed for camera {camera_id}: "
                f"compliant={detection_result.is_compliant}, id={detection_id}"
            )

        except Exception as e:
            self.logger.error(f"Error in processing pipeline for camera {camera_id}: {e}")

    def process_single_frame(
        self,
        frame: np.ndarray,
        camera_id: int
    ) -> Optional[int]:
        """
        Process a single frame through the pipeline

        Args:
            frame: Video frame
            camera_id: Camera ID

        Returns:
            Detection ID or None
        """
        return self._process_pipeline(frame, camera_id, time.time())

    def add_camera(
        self,
        name: str,
        location: str,
        rtsp_url: str
    ) -> Optional[int]:
        """
        Add a new camera to the system

        Args:
            name: Camera name
            location: Camera location
            rtsp_url: RTSP URL

        Returns:
            Camera ID or None
        """
        try:
            # Create camera in database
            from models.schemas import CameraCreate

            camera_create = CameraCreate(
                name=name,
                location=location,
                rtsp_url=rtsp_url,
                is_active=True
            )

            camera_response = self.database_service.create_camera(camera_create)

            # Add to camera service
            self.camera_service.add_camera(
                camera_id=camera_response.id,
                source_url=rtsp_url,
                name=name,
                location=location
            )

            # Start processing if system is running
            if self.is_running:
                self.camera_service.start_camera(camera_response.id)
                self._start_camera_processing(camera_response.id)

            self.logger.info(f"Added camera: {name}")

            return camera_response.id

        except Exception as e:
            self.logger.error(f"Error adding camera: {e}")
            return None

    def remove_camera(self, camera_id: int) -> bool:
        """
        Remove a camera from the system

        Args:
            camera_id: Camera ID

        Returns:
            True if removed successfully
        """
        try:
            # Stop processing
            if self.is_running:
                self.camera_service.stop_camera(camera_id)
                self._stop_camera_processing(camera_id)

            # Remove from camera service
            self.camera_service.remove_camera(camera_id)

            # Deactivate in database
            from models.schemas import CameraUpdate

            camera_update = CameraUpdate(is_active=False)
            self.database_service.update_camera(camera_id, camera_update)

            self.logger.info(f"Removed camera {camera_id}")

            return True

        except Exception as e:
            self.logger.error(f"Error removing camera: {e}")
            return False

    def get_system_stats(self) -> Dict[str, Any]:
        """
        Get current system statistics

        Returns:
            Statistics dictionary
        """
        stats = self.stats.copy()

        # Add uptime
        if stats["start_time"]:
            uptime = datetime.now() - stats["start_time"]
            stats["uptime"] = str(timedelta(seconds=int(uptime.total_seconds())))

        # Add active cameras
        stats["active_cameras"] = len(self.camera_service.cameras)

        # Calculate compliance rate
        if stats["total_detections"] > 0:
            compliant = stats["total_detections"] - stats["non_compliant_detections"]
            stats["compliance_rate"] = round((compliant / stats["total_detections"]) * 100, 2)
        else:
            stats["compliance_rate"] = 0.0

        return stats

    def get_system_status(self) -> Dict[str, Any]:
        """
        Get current system status

        Returns:
            Status dictionary
        """
        cameras_info = self.camera_service.get_all_cameras_info()

        return {
            "is_running": self.is_running,
            "active_cameras": len([c for c in cameras_info if c.get("is_running", False)]),
            "total_cameras": len(cameras_info),
            "cameras": cameras_info,
            "stats": self.get_system_stats()
        }

    def add_detection_callback(self, callback: Callable):
        """
        Add a callback to be called on each detection

        Args:
            callback: Callback function
        """
        self.detection_callbacks.append(callback)

    def _trigger_detection_callbacks(
        self,
        detection_result: DetectionResult,
        camera_id: int
    ):
        """
        Trigger all detection callbacks

        Args:
            detection_result: Detection result
            camera_id: Camera ID
        """
        for callback in self.detection_callbacks:
            try:
                callback(detection_result, camera_id)
            except Exception as e:
                self.logger.error(f"Error in detection callback: {e}")

    def sync_agents(self) -> bool:
        """
        Synchronize all agents and ensure consistency

        Returns:
            True if synchronized successfully
        """
        try:
            self.logger.info("Synchronizing agents...")

            # Reload camera configuration from database
            self._initialize_cameras()

            # Ensure all active cameras are running
            if self.is_running:
                for camera_id in self.camera_service.cameras:
                    if camera_id not in self.processing_threads:
                        self._start_camera_processing(camera_id)

            self.logger.info("Agents synchronized successfully")

            return True

        except Exception as e:
            self.logger.error(f"Error synchronizing agents: {e}")
            return False

    def handle_error(self, agent_name: str, error: Exception):
        """
        Handle error from an agent

        Args:
            agent_name: Name of the agent
            error: Exception that occurred
        """
        self.logger.error(f"Error in {agent_name}: {error}")

        # Implement retry logic or recovery strategies here
        # For now, just log the error

    def run_pipeline_for_duration(
        self,
        camera_id: int,
        duration: int = 60
    ) -> Dict[str, Any]:
        """
        Run pipeline for a specific duration

        Args:
            camera_id: Camera ID
            duration: Duration in seconds

        Returns:
            Statistics dictionary
        """
        self.logger.info(f"Running pipeline for camera {camera_id} for {duration} seconds")

        # Reset stats
        start_stats = {
            "total_frames_processed": 0,
            "total_detections": 0,
            "non_compliant_detections": 0
        }

        start_time = time.time()
        initial_stats = self.stats.copy()

        # Run for specified duration
        while time.time() - start_time < duration:
            time.sleep(1)

        # Calculate stats for this run
        run_stats = {
            "duration": duration,
            "frames_processed": self.stats["total_frames_processed"] - initial_stats["total_frames_processed"],
            "detections": self.stats["total_detections"] - initial_stats["total_detections"],
            "non_compliant": self.stats["non_compliant_detections"] - initial_stats["non_compliant_detections"]
        }

        if run_stats["detections"] > 0:
            run_stats["compliance_rate"] = round(
                ((run_stats["detections"] - run_stats["non_compliant"]) / run_stats["detections"]) * 100,
                2
            )
        else:
            run_stats["compliance_rate"] = 0.0

        self.logger.info(
            f"Pipeline completed: {run_stats['detections']} detections, "
            f"{run_stats['compliance_rate']}% compliance"
        )

        return run_stats


def get_orchestrator_agent() -> OrchestratorAgent:
    """
    Get or create orchestrator agent instance

    Returns:
        OrchestratorAgent: Orchestrator agent instance
    """
    return OrchestratorAgent()
