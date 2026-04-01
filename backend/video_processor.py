"""
Video Processing Module for EPI Recognition System

Handles video file processing, metadata extraction, and frame extraction
for training dataset creation.
"""
import os
import cv2
import uuid
import logging
import subprocess
import shutil
import json
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


def get_video_duration(video_path: str) -> int:
    """
    Detect video duration using ffprobe (more reliable than OpenCV).

    Args:
        video_path: Path to video file

    Returns:
        Duration in seconds, or 0 if detection fails
    """
    try:
        cmd = [
            'ffprobe', '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            os.path.abspath(video_path)
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = int(float(data['format']['duration']))
            logger.info(f"✅ Detected duration with ffprobe: {duration}s")
            return duration
    except Exception as e:
        logger.warning(f"ffprobe failed, falling back to OpenCV: {e}")

    # Fallback to OpenCV
    try:
        cap = cv2.VideoCapture(video_path)
        if cap.isOpened():
            fps = cap.get(cv2.CAP_PROP_FPS) or 30
            frame_count = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0
            duration = int(frame_count / fps) if fps > 0 else 0
            cap.release()
            logger.info(f"✅ Detected duration with OpenCV: {duration}s")
            return duration
    except Exception as e:
        logger.error(f"Failed to detect duration: {e}")
        return 0


class VideoProcessor:
    """Handle video upload and frame extraction"""

    def __init__(self, upload_dir: str = "uploads/videos"):
        """
        Initialize VideoProcessor.

        Args:
            upload_dir: Base directory for video storage
        """
        self.upload_dir = upload_dir
        os.makedirs(upload_dir, exist_ok=True)

    def process_video(
        self,
        db: Session,
        project_id: str,
        user_id: str,
        video_path: str,
        filename: str
    ) -> Dict[str, Any]:
        """
        Process uploaded video: extract metadata and save to database.

        Args:
            db: Database session
            project_id: Project UUID
            user_id: User UUID
            video_path: Path to uploaded video file
            filename: Original filename

        Returns:
            Dictionary with success status and video data
        """
        try:
            # Open video file
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {
                    'success': False,
                    'error': 'Invalid video file or unsupported format'
                }

            # Get video metadata
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            # Calculate duration
            if fps > 0:
                duration = frame_count / fps
            else:
                duration = 0

            cap.release()

            # Generate video ID and storage path
            video_id = str(uuid.uuid4())
            project_dir = os.path.join(self.upload_dir, project_id)
            os.makedirs(project_dir, exist_ok=True)

            storage_path = os.path.join(project_dir, f"{video_id}.{filename.split('.')[-1]}")

            # Copy video to storage
            import shutil
            shutil.copy(video_path, storage_path)
            logger.info(f"✅ Video saved to: {storage_path}")

            # Detect duration using ffprobe (more reliable)
            duration = get_video_duration(storage_path)
            if duration == 0:
                logger.warning(f"⚠️  Could not detect duration for {filename}")

            # Save to database using VideoService
            from backend.video_db import VideoService
            video_service = VideoService()

            video = video_service.upload_video(
                db=db,
                project_id=project_id,
                user_id=user_id,
                filename=filename,
                storage_path=storage_path,
                duration=duration,
                frame_count=frame_count,
                fps=fps
            )

            logger.info(
                f"✅ Video processed: {filename} "
                f"({duration:.2f}s, {frame_count} frames, {fps:.2f} fps)"
            )

            return {
                'success': True,
                'video': video
            }

        except Exception as e:
            logger.error(f"❌ Error processing video: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _extract_chunk_ffmpeg(
        self,
        video_path: str,
        output_dir: str,
        chunk_num: int,
        start_second: int,
        duration: int = 60
    ) -> int:
        """
        Extract frames from one chunk using FFmpeg (10-15x faster than OpenCV).

        Args:
            video_path: Path to video file
            output_dir: Directory to save frames
            chunk_num: Chunk number
            start_second: Start time in seconds
            duration: Duration in seconds (default 60)

        Returns:
            Number of frames extracted
        """
        os.makedirs(output_dir, exist_ok=True)

        cmd = [
            'ffmpeg', '-y',
            '-ss', str(start_second),        # fast seek BEFORE -i
            '-i', video_path,
            '-t', str(duration),
            '-vf', 'fps=1,scale=960:-1',     # 1fps, 960px width
            '-q:v', '8',                      # medium-good quality
            f'{output_dir}/frame_{chunk_num:02d}_%05d.jpg'
        ]

        result = subprocess.run(cmd, capture_output=True, timeout=120)

        if result.returncode != 0:
            error_msg = result.stderr.decode()[:200] if result.stderr else 'Unknown error'
            raise Exception(f"FFmpeg error chunk {chunk_num}: {error_msg}")

        # Count extracted frames
        frames = [f for f in os.listdir(output_dir) if f.endswith('.jpg')]
        return len(frames)

    def _save_frames_to_db(
        self,
        frames_dir: str,
        video_id: str,
        db: Session,
        chunk_num: int = 0
    ) -> int:
        """
        Save extracted frames to database.

        Args:
            frames_dir: Directory containing frame images
            video_id: Video UUID
            db: Database session
            chunk_num: Chunk number for frame numbering

        Returns:
            Number of frames saved
        """
        frame_files = sorted([f for f in os.listdir(frames_dir) if f.endswith('.jpg')])
        saved_count = 0
        chunk_offset = chunk_num * 1000  # Assume max 1000 frames per chunk

        for frame_file in frame_files:
            frame_path = os.path.join(frames_dir, frame_file)

            # Extract frame number from filename (frame_XX_00567.jpg -> 567)
            try:
                parts = frame_file.replace('.jpg', '').split('_')
                local_frame_num = int(parts[-1])
                global_frame_num = chunk_offset + local_frame_num
            except (ValueError, IndexError):
                global_frame_num = chunk_offset + saved_count

            frame_id = str(uuid.uuid4())
            insert_query = text("""
                INSERT INTO training_frames (id, video_id, frame_number, storage_path, is_annotated, created_at)
                VALUES (:id, :video_id, :frame_number, :storage_path, FALSE, NOW())
            """)

            db.execute(insert_query, {
                'id': frame_id,
                'video_id': video_id,
                'frame_number': global_frame_num,
                'storage_path': frame_path
            })

            saved_count += 1

            # Log progress every 100 frames
            if saved_count % 100 == 0:
                logger.info(f"   Chunk {chunk_num}: Saved {saved_count} frames...")

        db.commit()
        return saved_count

    def extract_frames(
        self,
        db: Session,
        video_id: str,
        user_id: str,
        frames_per_second: int = 1,
        max_frames: Optional[int] = None,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Extract frames from video for annotation using FFmpeg (optimized) or OpenCV (fallback).

        Args:
            db: Database session
            video_id: Video UUID
            user_id: User UUID (for ownership verification)
            frames_per_second: Number of frames to extract per second
            max_frames: Maximum number of frames to extract (optional)
            start_time: Start time in seconds (optional, for segment extraction)
            end_time: End time in seconds (optional, for segment extraction)

        Returns:
            Dictionary with success status and extracted frames count
        """
        try:
            from backend.video_db import VideoService
            video_service = VideoService()

            # Get video record
            video = video_service.get_video(db, video_id, user_id)
            if not video:
                return {
                    'success': False,
                    'error': 'Video not found or access denied'
                }

            video_path = video['storage_path']
            if not os.path.exists(video_path):
                return {
                    'success': False,
                    'error': f'Video file not found at {video_path}'
                }

            # Validate time range if provided
            video_duration = video.get('duration_seconds', 0)
            if start_time is not None and end_time is not None:
                # Both provided - validate segment extraction
                if start_time < 0 or end_time < 0:
                    return {
                        'success': False,
                        'error': 'Start time and end time must be non-negative'
                    }

                if start_time >= end_time:
                    return {
                        'success': False,
                        'error': 'Start time must be less than end time'
                    }

                segment_duration = end_time - start_time
                if segment_duration < 60:
                    return {
                        'success': False,
                        'error': f'Segment duration too short: {segment_duration}s (minimum: 60s)'
                    }

                if video_duration > 0 and end_time > video_duration:
                    return {
                        'success': False,
                        'error': f'End time ({end_time}s) exceeds video duration ({video_duration}s)'
                    }

                logger.info(f"🎬 Extracting segment: {start_time}s - {end_time}s ({segment_duration}s total)")

            elif start_time is not None or end_time is not None:
                # Only one provided - invalid
                return {
                    'success': False,
                    'error': 'Both start_time and end_time must be provided together'
                }
            else:
                logger.info(f"🎬 Extracting full video {video_id}...")

            # Create frames base directory
            frames_base_dir = os.path.join(
                os.path.dirname(video_path),
                f"frames_{video_id}"
            )
            os.makedirs(frames_base_dir, exist_ok=True)

            # Check if FFmpeg is available
            if shutil.which('ffmpeg'):
                return self._extract_frames_ffmpeg(
                    video_path, frames_base_dir, video_id, db, user_id, max_frames,
                    start_time, end_time
                )
            else:
                logger.warning("FFmpeg not found, falling back to OpenCV (slower)")
                return self._extract_frames_opencv(
                    video_path, frames_base_dir, video_id, db, user_id, max_frames,
                    start_time, end_time
                )

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error extracting frames: {e}")
            return {
                'success': False,
                'error': str(e)
            }

    def _extract_frames_ffmpeg(
        self,
        video_path: str,
        output_base_dir: str,
        video_id: str,
        db: Session,
        user_id: str,
        max_frames: Optional[int],
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Extract frames using FFmpeg with parallel chunk processing (10-15x faster).

        Args:
            video_path: Path to video file
            output_base_dir: Base directory for frames
            video_id: Video UUID
            db: Database session
            user_id: User UUID
            max_frames: Maximum frames to extract
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)

        Returns:
            Dictionary with success status and extracted frames count
        """
        try:
            from backend.video_db import VideoService
            video_service = VideoService()

            # Get video duration
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {
                    'success': False,
                    'error': 'Failed to open video file'
                }

            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration_sec = total_frames / fps if fps > 0 else 0
            cap.release()

            logger.info(f"   - Duration: {duration_sec:.2f}s, FPS: {fps:.2f}")

            total_frames_extracted = 0

            # If start_time and end_time provided, extract single segment
            if start_time is not None and end_time is not None:
                segment_duration = end_time - start_time
                logger.info(f"   - Extracting segment: {start_time}s - {end_time}s ({segment_duration}s)")

                chunk_dir = os.path.join(output_base_dir, "segment")
                frames_count = self._extract_chunk_ffmpeg(
                    video_path, chunk_dir, 0, start_time, segment_duration
                )

                # Save to database
                saved = self._save_frames_to_db(chunk_dir, video_id, db, 0)
                total_frames_extracted = saved

                logger.info(f"   - Segment extraction complete: {saved} frames")

                # Mark as completed
                try:
                    db.execute(text("""
                        UPDATE training_videos
                        SET status = 'completed',
                            processed_chunks = 1,
                            total_chunks = 1
                        WHERE id = :video_id
                    """), {'video_id': video_id})
                    db.commit()
                except Exception as e:
                    logger.warning(f"Could not update status to completed: {e}")

            else:
                # Full video extraction - Calculate chunks (60 seconds each)
                chunk_duration = 60
                total_chunks = int(duration_sec / chunk_duration) + (1 if duration_sec % chunk_duration > 0 else 0)

                # Limit by max_frames
                if max_frames:
                    total_chunks = min(total_chunks, int(max_frames / 60) + 1)

                logger.info(f"   - Extracting {total_chunks} chunks in parallel...")

                max_workers = min(4, total_chunks)

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}

                    for chunk in range(total_chunks):
                        chunk_start = chunk * chunk_duration
                        chunk_dir = os.path.join(output_base_dir, f"chunk_{chunk:02d}")

                        future = executor.submit(
                            self._extract_chunk_ffmpeg,
                            video_path, chunk_dir, chunk, chunk_start, chunk_duration
                        )
                        futures[future] = chunk

                    for future in as_completed(futures):
                        chunk_num = futures[future]
                        try:
                            frames_count = future.result()

                            # Save to database
                            chunk_dir = os.path.join(output_base_dir, f"chunk_{chunk_num:02d}")
                            saved = self._save_frames_to_db(chunk_dir, video_id, db, chunk_num)
                            total_frames_extracted += saved

                            logger.info(f"   Chunk {chunk_num:02d}: {saved} frames")

                            # Update progress
                            try:
                                db.execute(text("""
                                    UPDATE training_videos
                                    SET processed_chunks = processed_chunks + 1,
                                        status = 'extracting'
                                    WHERE id = :video_id
                                """), {'video_id': video_id})
                                db.commit()
                            except Exception as e:
                                logger.warning(f"Could not update progress: {e}")

                        except Exception as e:
                            logger.error(f"   Chunk {chunk_num} failed: {e}")
                            continue

                # Mark as completed
                try:
                    db.execute(text("""
                        UPDATE training_videos
                    SET status = 'completed',
                        processed_chunks = total_chunks
                    WHERE id = :video_id
                """), {'video_id': video_id})
                db.commit()
            except Exception as e:
                logger.warning(f"Could not update status to completed: {e}")

            logger.info(f"✅ FFmpeg extraction complete: {total_frames_extracted} frames")

            return {
                'success': True,
                'extracted_frames': total_frames_extracted,
                'frames_dir': output_base_dir
            }

        except Exception as e:
            # Mark as failed
            try:
                db.execute(text("""
                    UPDATE training_videos SET status = 'failed' WHERE id = :video_id
                """), {'video_id': video_id})
                db.commit()
            except:
                pass

            raise

    def _extract_frames_opencv(
        self,
        video_path: str,
        frames_dir: str,
        video_id: str,
        db: Session,
        user_id: str,
        max_frames: Optional[int],
        start_time: Optional[int] = None,
        end_time: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Extract frames using OpenCV (fallback, slower but works without FFmpeg).

        Args:
            video_path: Path to video file
            frames_dir: Directory for frames
            video_id: Video UUID
            db: Database session
            user_id: User UUID
            max_frames: Maximum frames to extract
            start_time: Start time in seconds (optional)
            end_time: End time in seconds (optional)

        Returns:
            Dictionary with success status and extracted frames count
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return {
                'success': False,
                'error': 'Failed to open video file'
            }

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Calculate frame interval (1 fps)
        if fps > 0:
            interval = int(fps / 1)
        else:
            interval = 1

        os.makedirs(frames_dir, exist_ok=True)

        extracted_count = 0
        frame_number = 0

        logger.info(f"   - Using OpenCV (slower), Interval: every {interval} frames")

        # If segment extraction, jump to start_time
        start_frame = 0
        end_frame = total_frames

        if start_time is not None and end_time is not None:
            start_frame = int(start_time * fps)
            end_frame = int(end_time * fps)
            logger.info(f"   - Segment extraction: frame {start_frame} to {end_frame}")

            # Jump to start frame
            cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
            frame_number = start_frame

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Check if we've reached end_frame for segment extraction
            if start_time is not None and end_time is not None:
                if frame_number >= end_frame:
                    break

            if max_frames and extracted_count >= max_frames:
                break

            if frame_number % interval == 0:
                frame_filename = f'frame_{extracted_count:06d}.jpg'
                frame_path = os.path.join(frames_dir, frame_filename)

                # Resize and save
                resized_frame = cv2.resize(frame, (960, 540), interpolation=cv2.INTER_AREA)
                cv2.imwrite(frame_path, resized_frame, [cv2.IMWRITE_JPEG_QUALITY, 8])

                # Save to database
                frame_id = str(uuid.uuid4())
                insert_query = text("""
                    INSERT INTO training_frames (id, video_id, frame_number, storage_path, is_annotated, created_at)
                    VALUES (:id, :video_id, :frame_number, :storage_path, FALSE, NOW())
                """)

                db.execute(insert_query, {
                    'id': frame_id,
                    'video_id': video_id,
                    'frame_number': extracted_count,
                    'storage_path': frame_path
                })

                extracted_count += 1

                if extracted_count % 100 == 0:
                    logger.info(f"   Extracted {extracted_count} frames...")

            frame_number += 1

        db.commit()
        cap.release()

        logger.info(f"✅ OpenCV extraction complete: {extracted_count} frames")

        return {
            'success': True,
            'extracted_frames': extracted_count,
            'frames_dir': frames_dir
        }

    def get_video_info(self, video_path: str) -> Dict[str, Any]:
        """
        Get video metadata without processing.

        Args:
            video_path: Path to video file

        Returns:
            Dictionary with video metadata
        """
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {
                    'success': False,
                    'error': 'Failed to open video file'
                }

            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            duration = frame_count / fps if fps > 0 else 0

            cap.release()

            return {
                'success': True,
                'fps': fps,
                'frame_count': frame_count,
                'width': width,
                'height': height,
                'duration': duration
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


# Export processor class
__all__ = ['VideoProcessor']
