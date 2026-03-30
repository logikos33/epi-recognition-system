import subprocess
import os
import shutil
import threading
import time
import logging
import signal
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class StreamManager:
    """Manages FFmpeg subprocesses for HLS streaming with health monitoring"""

    def __init__(self, hls_base_dir: str = './streams', health_check_interval: int = 30):
        self.hls_base_dir = hls_base_dir
        self.active_streams: Dict[int, subprocess.Popen] = {}
        self.stream_metadata: Dict[int, Dict] = {}  # Store metadata for each stream
        self.lock = threading.Lock()
        self.health_check_interval = health_check_interval  # seconds
        self._health_check_thread: Optional[threading.Thread] = None
        self._stop_health_check = threading.Event()

        os.makedirs(self.hls_base_dir, exist_ok=True)
        logger.info(f"StreamManager initialized with base directory: {self.hls_base_dir}")

        # Start health check thread
        self._start_health_check_thread()

    def start_stream(self, camera_id: int, rtsp_url: str) -> Dict:
        """Start FFmpeg subprocess for a camera"""
        with self.lock:
            # Check if stream already exists
            if camera_id in self.active_streams:
                process = self.active_streams[camera_id]
                if process.poll() is None:
                    logger.warning(f"Stream for camera {camera_id} already running")
                    return {
                        'status': 'already_running',
                        'hls_url': f'/streams/{camera_id}/stream.m3u8'
                    }
                else:
                    # Clean up dead process
                    del self.active_streams[camera_id]

            # Create output directory for this camera
            output_dir = os.path.join(self.hls_base_dir, str(camera_id))
            os.makedirs(output_dir, exist_ok=True)

            # Clean up old HLS files if they exist
            self._cleanup_hls_files(output_dir)

            # Build FFmpeg command for HLS streaming
            output_path = os.path.join(output_dir, 'stream.m3u8')

            ffmpeg_cmd = [
                'ffmpeg',
                '-rtsp_transport', 'tcp',
                '-i', rtsp_url,
                '-c:v', 'libx264',
                '-preset', 'ultrafast',
                '-tune', 'zerolatency',
                '-b:v', '512k',
                '-s', '640x360',
                '-f', 'hls',
                '-hls_time', '1',
                '-hls_list_size', '3',
                '-hls_flags', 'delete_segments',
                '-y',  # Overwrite output file
                output_path
            ]

            try:
                logger.info(f"Starting FFmpeg for camera {camera_id}: {' '.join(ffmpeg_cmd)}")

                # Start FFmpeg subprocess
                process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL
                )

                self.active_streams[camera_id] = process

                # Wait a moment to ensure FFmpeg starts successfully
                time.sleep(1)

                # Check if process is still running
                if process.poll() is None:
                    logger.info(f"Successfully started stream for camera {camera_id}")

                    # Store metadata for health monitoring
                    self.stream_metadata[camera_id] = {
                        'rtsp_url': rtsp_url,
                        'started_at': datetime.now(),
                        'last_health_check': datetime.now(),
                        'restart_count': 0,
                        'pid': process.pid
                    }

                    return {
                        'status': 'started',
                        'hls_url': f'/streams/{camera_id}/stream.m3u8',
                        'camera_id': camera_id
                    }
                else:
                    # FFmpeg failed to start
                    stderr_output = process.stderr.read().decode('utf-8', errors='ignore')
                    logger.error(f"FFmpeg failed to start for camera {camera_id}: {stderr_output}")
                    del self.active_streams[camera_id]
                    return {
                        'status': 'error',
                        'error': 'FFmpeg process terminated unexpectedly',
                        'details': stderr_output[:500]  # First 500 chars of error
                    }

            except Exception as e:
                logger.error(f"Failed to start stream for camera {camera_id}: {str(e)}")
                return {
                    'status': 'error',
                    'error': str(e)
                }

    def stop_stream(self, camera_id: int) -> bool:
        """Stop stream and clean up HLS files"""
        with self.lock:
            if camera_id not in self.active_streams:
                logger.warning(f"No active stream found for camera {camera_id}")
                return False

            process = self.active_streams[camera_id]

            try:
                # Terminate the FFmpeg process
                process.terminate()

                # Wait up to 5 seconds for graceful termination
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    logger.warning(f"FFmpeg for camera {camera_id} did not terminate gracefully, killing")
                    process.kill()
                    process.wait()

                logger.info(f"Stopped stream for camera {camera_id}")

                # Clean up HLS files
                output_dir = os.path.join(self.hls_base_dir, str(camera_id))
                self._cleanup_hls_files(output_dir)

                # Remove from active streams
                del self.active_streams[camera_id]

                return True

            except Exception as e:
                logger.error(f"Error stopping stream for camera {camera_id}: {str(e)}")
                return False

    def get_stream_status(self, camera_id: int) -> Dict:
        """Get status of a camera stream"""
        with self.lock:
            if camera_id not in self.active_streams:
                return {
                    'status': 'idle',
                    'hls_url': None
                }

            process = self.active_streams[camera_id]

            # Check if process is still running
            if process.poll() is None:
                return {
                    'status': 'streaming',
                    'hls_url': f'/streams/{camera_id}/stream.m3u8',
                    'camera_id': camera_id,
                    'pid': process.pid
                }
            else:
                # Process died, clean up
                del self.active_streams[camera_id]
                return {
                    'status': 'error',
                    'hls_url': None,
                    'error': 'FFmpeg process terminated unexpectedly'
                }

    def get_all_streams_status(self) -> Dict:
        """Get status of all camera streams"""
        with self.lock:
            streams = {}

            for camera_id, process in list(self.active_streams.items()):
                if process.poll() is None:
                    streams[camera_id] = {
                        'status': 'streaming',
                        'hls_url': f'/streams/{camera_id}/stream.m3u8',
                        'pid': process.pid
                    }
                else:
                    # Clean up dead processes
                    streams[camera_id] = {
                        'status': 'error',
                        'hls_url': None,
                        'error': 'FFmpeg process terminated'
                    }
                    del self.active_streams[camera_id]

            return {
                'total_active': len(self.active_streams),
                'streams': streams
            }

    def _cleanup_hls_files(self, output_dir: str):
        """Remove all HLS files from output directory"""
        try:
            if os.path.exists(output_dir):
                # Remove all files in the directory
                for filename in os.listdir(output_dir):
                    file_path = os.path.join(output_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            logger.debug(f"Removed HLS file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to remove {file_path}: {str(e)}")

                # Optionally remove the directory itself
                try:
                    os.rmdir(output_dir)
                    logger.debug(f"Removed HLS directory: {output_dir}")
                except:
                    pass  # Directory not empty or other error

        except Exception as e:
            logger.warning(f"Error cleaning up HLS files in {output_dir}: {str(e)}")

    def stop_all_streams(self):
        """Stop all active streams (useful for shutdown)"""
        with self.lock:
            logger.info(f"Stopping all {len(self.active_streams)} streams")
            for camera_id in list(self.active_streams.keys()):
                self.stop_stream(camera_id)

    # ========================================================================
    # Health Monitoring & Auto-Restart (Task 17)
    # ========================================================================

    def _start_health_check_thread(self):
        """Start background thread for health monitoring"""
        self._health_check_thread = threading.Thread(
            target=self._health_check_loop,
            daemon=True,
            name='StreamHealthCheck'
        )
        self._health_check_thread.start()
        logger.info("Health check thread started")

    def _health_check_loop(self):
        """Periodically check health of all streams and restart dead ones"""
        while not self._stop_health_check.is_set():
            try:
                self._check_all_streams_health()
                self._stop_health_check.wait(self.health_check_interval)
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                self._stop_health_check.wait(5)  # Wait 5s before retry

        logger.info("Health check thread stopped")

    def _check_all_streams_health(self):
        """Check health of all active streams and restart if needed"""
        with self.lock:
            dead_streams = []

            for camera_id, process in self.active_streams.items():
                # Check if process is still running
                if process.poll() is not None:
                    logger.warning(f"Stream {camera_id} process died (exit code: {process.poll()})")
                    dead_streams.append(camera_id)
                else:
                    # Update metadata
                    if camera_id in self.stream_metadata:
                        self.stream_metadata[camera_id]['last_health_check'] = datetime.now()
                        self.stream_metadata[camera_id]['pid'] = process.pid

            # Restart dead streams
            for camera_id in dead_streams:
                self._restart_dead_stream(camera_id)

    def _restart_dead_stream(self, camera_id: int):
        """Attempt to restart a dead stream"""
        logger.info(f"Attempting to restart stream {camera_id}")

        # Get metadata
        if camera_id not in self.stream_metadata:
            logger.error(f"No metadata found for dead stream {camera_id}, cannot restart")
            return

        metadata = self.stream_metadata[camera_id]
        restart_count = metadata.get('restart_count', 0)
        max_restarts = 3

        if restart_count >= max_restarts:
            logger.error(f"Max restart attempts ({max_restarts}) reached for camera {camera_id}")
            self.stop_stream(camera_id)  # Clean up
            return

        # Clean up dead process
        if camera_id in self.active_streams:
            del self.active_streams[camera_id]

        # Attempt restart
        try:
            result = self.start_stream(camera_id, metadata['rtsp_url'])
            if result['status'] == 'started':
                logger.info(f"Successfully restarted stream {camera_id} (attempt {restart_count + 1}/{max_restarts})")
                self.stream_metadata[camera_id]['restart_count'] = restart_count + 1
                self.stream_metadata[camera_id]['last_restarted_at'] = datetime.now()
            else:
                logger.error(f"Failed to restart stream {camera_id}: {result.get('error')}")
        except Exception as e:
            logger.error(f"Error restarting stream {camera_id}: {e}")

    def get_stream_health_report(self) -> Dict:
        """Get detailed health report for all streams"""
        with self.lock:
            report = {
                'total_streams': len(self.active_streams),
                'streams': [],
                'timestamp': datetime.now().isoformat()
            }

            for camera_id, process in self.active_streams.items():
                metadata = self.stream_metadata.get(camera_id, {})
                is_healthy = process.poll() is None

                stream_info = {
                    'camera_id': camera_id,
                    'is_healthy': is_healthy,
                    'pid': process.pid if is_healthy else None,
                    'exit_code': process.poll() if not is_healthy else None,
                    'started_at': metadata.get('started_at'),
                    'last_health_check': metadata.get('last_health_check'),
                    'restart_count': metadata.get('restart_count', 0),
                    'last_restarted_at': metadata.get('last_restarted_at'),
                    'uptime_seconds': None
                }

                # Calculate uptime
                if metadata.get('started_at'):
                    started_at = metadata['started_at']
                    if isinstance(started_at, str):
                        started_at = datetime.fromisoformat(started_at)
                    uptime = datetime.now() - started_at
                    stream_info['uptime_seconds'] = uptime.total_seconds()

                report['streams'].append(stream_info)

            return report

    def stop_health_check(self):
        """Stop health check thread (for shutdown)"""
        logger.info("Stopping health check thread")
        self._stop_health_check.set()
        if self._health_check_thread:
            self._health_check_thread.join(timeout=5)
            logger.info("Health check thread stopped")
