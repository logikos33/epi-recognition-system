import subprocess
import os
import shutil
import threading
import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class StreamManager:
    """Manages FFmpeg subprocesses for HLS streaming"""

    def __init__(self, hls_base_dir: str = './streams'):
        self.hls_base_dir = hls_base_dir
        self.active_streams: Dict[int, subprocess.Popen] = {}
        self.lock = threading.Lock()
        os.makedirs(self.hls_base_dir, exist_ok=True)
        logger.info(f"StreamManager initialized with base directory: {self.hls_base_dir}")

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
