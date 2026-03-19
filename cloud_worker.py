#!/usr/bin/env python3
"""
Cloud Worker - Background worker for processing RTSP streams in the cloud
Runs on Render/Railway and processes camera frames with YOLO

Usage:
    python cloud_worker.py
"""
import asyncio
import signal
import sys
import time
from datetime import datetime
from typing import Dict, List, Any, Optional
import cv2
import numpy as np

from utils.logger import get_logger, setup_logging
from utils.config import get_config
from utils.camera_helpers import build_rtsp_url, test_rtsp_connection, CameraBrand
from services.supabase_service import get_supabase_service
from services.yolo_service import YOLOService


class CloudWorker:
    """
    Cloud worker that connects to RTSP streams, processes frames with YOLO,
    and writes detection results to Supabase
    """

    def __init__(self):
        """Initialize cloud worker"""
        self.logger = get_logger(__name__)
        self.config = get_config()

        # Worker identification
        self.worker_id = self.config.worker_id
        self.camera_range_start = self.config.camera_range_start
        self.camera_range_end = self.config.camera_range_end

        # Processing settings
        self.frame_rate = self.config.frame_rate
        self.frames_per_batch = self.config.frames_per_batch
        self.heartbeat_interval = self.config.worker_heartbeat_interval
        self.rtsp_timeout = self.config.rtsp_connection_timeout

        # Services
        self.supabase = get_supabase_service()
        self.yolo = YOLOService()

        # State
        self.is_running = False
        self.active_connections: Dict[int, cv2.VideoCapture] = {}
        self.last_heartbeat = datetime.now()

        self.logger.info(
            f"CloudWorker {self.worker_id} initialized "
            f"(cameras {self.camera_range_start}-{self.camera_range_end})"
        )

    def start(self):
        """Start the worker main loop"""
        self.is_running = True
        self.logger.info(f"Worker {self.worker_id} starting...")

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        try:
            asyncio.run(self._main_loop())
        except Exception as e:
            self.logger.error(f"Worker error: {e}", exc_info=True)
        finally:
            self.stop()

    def stop(self):
        """Stop the worker and cleanup resources"""
        self.logger.info(f"Worker {self.worker_id} stopping...")
        self.is_running = False

        # Close all RTSP connections
        for camera_id, cap in self.active_connections.items():
            try:
                cap.release()
                self.logger.debug(f"Closed connection for camera {camera_id}")
            except Exception as e:
                self.logger.error(f"Error closing camera {camera_id}: {e}")

        self.active_connections.clear()

        # Update worker status
        self.supabase.update_worker_heartbeat(
            self.worker_id,
            [],
            status="stopped"
        )

        self.logger.info("Worker stopped")

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.stop()
        sys.exit(0)

    async def _main_loop(self):
        """Main processing loop"""
        self.logger.info("Main loop started")

        while self.is_running:
            try:
                # Get cameras to process
                cameras = self._get_cameras_to_process()

                if not cameras:
                    self.logger.info("No cameras to process, waiting...")
                    await asyncio.sleep(10)
                    continue

                self.logger.info(f"Processing {len(cameras)} camera(s)")

                # Process each camera
                for camera in cameras:
                    if not self.is_running:
                        break

                    await self._process_camera(camera)

                # Update heartbeat
                await self._update_heartbeat(cameras)

                # Wait before next cycle
                cycle_time = self.frames_per_batch / self.frame_rate
                self.logger.debug(f"Cycle complete, waiting {cycle_time:.1f}s")
                await asyncio.sleep(max(1, cycle_time))

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}", exc_info=True)
                await asyncio.sleep(5)

    def _get_cameras_to_process(self) -> List[Dict[str, Any]]:
        """
        Get list of cameras to process

        Returns:
            List of camera dictionaries
        """
        try:
            # Get cameras in assigned range
            cameras = self.supabase.get_cameras_in_range(
                self.camera_range_start,
                self.camera_range_end
            )

            self.logger.debug(f"Found {len(cameras)} camera(s) in range")
            return cameras

        except Exception as e:
            self.logger.error(f"Error fetching cameras: {e}")
            return []

    async def _process_camera(self, camera: Dict[str, Any]):
        """
        Process frames from a single camera

        Args:
            camera: Camera configuration
        """
        camera_id = camera['id']
        camera_name = camera.get('name', f'Camera {camera_id}')

        try:
            # Build RTSP URL
            rtsp_url = build_rtsp_url(camera)
            if not rtsp_url:
                self.logger.error(f"Could not build RTSP URL for {camera_name}")
                return

            self.logger.debug(f"Processing {camera_name}: {rtsp_url[:50]}...")

            # Get or create connection
            cap = self._get_connection(camera_id, rtsp_url)
            if cap is None:
                return

            # Process batch of frames
            detections = []

            for frame_idx in range(self.frames_per_batch):
                if not self.is_running:
                    break

                ret, frame = cap.read()
                if not ret:
                    self.logger.warning(f"Failed to read frame {frame_idx} from {camera_name}")
                    break

                # Process frame with YOLO
                try:
                    result = self.yolo.detect_epis(frame)

                    # Create detection record
                    detection_data = {
                        "camera_id": camera_id,
                        "timestamp": result.timestamp.isoformat(),
                        "epis_detected": result.epis_detected,
                        "confidence": result.confidence,
                        "is_compliant": result.is_compliant,
                        "person_count": result.person_count
                    }

                    detections.append(detection_data)

                    if result.is_compliant:
                        self.logger.debug(
                            f"Frame {frame_idx}: {result.person_count} person(s), "
                            f"compliant={result.is_compliant}"
                        )
                    else:
                        self.logger.warning(
                            f"Frame {frame_idx}: {result.person_count} person(s), "
                            f"NON-COMPLIANT - missing EPIs: "
                            f"{[e for e, d in result.epis_detected.items() if not d]}"
                        )

                except Exception as e:
                    self.logger.error(f"Error processing frame: {e}")

            # Batch insert detections
            if detections:
                self._insert_detections_batch(detections)
                self.logger.info(
                    f"{camera_name}: Processed {len(detections)} frames, "
                    f"{sum(1 for d in detections if d['is_compliant'])} compliant"
                )

        except Exception as e:
            self.logger.error(f"Error processing camera {camera_name}: {e}")

    def _get_connection(self, camera_id: int, rtsp_url: str) -> Optional[cv2.VideoCapture]:
        """
        Get existing or create new RTSP connection

        Args:
            camera_id: Camera ID
            rtsp_url: RTSP URL

        Returns:
            VideoCapture object or None
        """
        # Check for existing connection
        if camera_id in self.active_connections:
            cap = self.active_connections[camera_id]
            if cap.isOpened():
                return cap
            else:
                # Connection died, remove it
                self.logger.warning(f"Camera {camera_id} connection died, reconnecting...")
                try:
                    cap.release()
                except:
                    pass
                del self.active_connections[camera_id]

        # Create new connection
        try:
            self.logger.info(f"Connecting to camera {camera_id}...")
            cap = cv2.VideoCapture(rtsp_url)

            if not cap.isOpened():
                self.logger.error(f"Failed to open RTSP stream for camera {camera_id}")
                return None

            # Configure stream
            cap.set(cv2.CAP_PROP_FPS, self.frame_rate)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

            # Try to read first frame
            ret, frame = cap.read()
            if not ret or frame is None:
                self.logger.error(f"Failed to read first frame from camera {camera_id}")
                cap.release()
                return None

            self.active_connections[camera_id] = cap
            self.logger.info(f"Connected to camera {camera_id} successfully")

            return cap

        except Exception as e:
            self.logger.error(f"Error connecting to camera {camera_id}: {e}")
            return None

    def _insert_detections_batch(self, detections: List[Dict[str, Any]]):
        """
        Insert batch of detections to Supabase

        Args:
            detections: List of detection dictionaries
        """
        try:
            for detection in detections:
                self.supabase.insert_detection(detection)
        except Exception as e:
            self.logger.error(f"Error inserting detections: {e}")

    async def _update_heartbeat(self, cameras: List[Dict[str, Any]]):
        """
        Update worker heartbeat status

        Args:
            cameras: List of cameras being processed
        """
        try:
            active_camera_ids = [c['id'] for c in cameras]
            status = "active" if cameras else "idle"

            self.supabase.update_worker_heartbeat(
                self.worker_id,
                active_camera_ids,
                status=status
            )

            self.last_heartbeat = datetime.now()

        except Exception as e:
            self.logger.error(f"Error updating heartbeat: {e}")


async def health_check_server():
    """
    Simple health check server for Render/Railway
    Responds to /health endpoint
    """
    from aiohttp import web

    async def health_handler(request):
        return web.json_response({
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        })

    app = web.Application()
    app.router.add_get('/health', health_handler)

    runner = web.AppRunner(app)
    await runner.setup()

    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()

    # Keep server running
    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        await runner.cleanup()


def main():
    """Main entry point"""
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)

    logger.info("=" * 60)
    logger.info("EPI Recognition Cloud Worker")
    logger.info("=" * 60)

    # Print configuration
    config = get_config()
    logger.info(f"Worker ID: {config.worker_id}")
    logger.info(f"Camera Range: {config.camera_range_start}-{config.camera_range_end}")
    logger.info(f"Frame Rate: {config.frame_rate} FPS per camera")
    logger.info(f"Frames per Batch: {config.frames_per_batch}")

    # Create and start worker
    worker = CloudWorker()

    try:
        worker.start()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
