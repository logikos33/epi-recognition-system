"""
Video Processing Module for EPI Recognition System

Handles video file processing, metadata extraction, and frame extraction
for training dataset creation.
"""
import os
import cv2
import uuid
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


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

    def extract_frames(
        self,
        db: Session,
        video_id: str,
        user_id: str,
        frames_per_second: int = 1,
        max_frames: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Extract frames from video for annotation.

        Args:
            db: Database session
            video_id: Video UUID
            user_id: User UUID (for ownership verification)
            frames_per_second: Number of frames to extract per second
            max_frames: Maximum number of frames to extract (optional)

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

            # Open video
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {
                    'success': False,
                    'error': 'Failed to open video file'
                }

            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

            # Calculate frame interval
            if fps > 0:
                interval = int(fps / frames_per_second)
            else:
                interval = 1  # Extract every frame if fps is 0

            # Create frames directory
            frames_dir = os.path.join(
                os.path.dirname(video_path),
                f"frames_{video_id}"
            )
            os.makedirs(frames_dir, exist_ok=True)

            extracted_count = 0
            frame_number = 0

            logger.info(f"🎬 Extracting frames from video {video_id}...")
            logger.info(f"   - FPS: {fps:.2f}, Total frames: {total_frames}")
            logger.info(f"   - Interval: every {interval} frames")
            if max_frames:
                logger.info(f"   - Max frames: {max_frames}")

            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break

                # Check max_frames limit
                if max_frames and extracted_count >= max_frames:
                    break

                # Extract frame at interval
                if frame_number % interval == 0:
                    frame_filename = f'frame_{extracted_count:06d}.jpg'
                    frame_path = os.path.join(frames_dir, frame_filename)

                    # Save frame
                    cv2.imwrite(frame_path, frame)

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

                    # Log progress every 100 frames
                    if extracted_count % 100 == 0:
                        logger.info(f"   Extracted {extracted_count} frames...")

                frame_number += 1

            db.commit()
            cap.release()

            logger.info(f"✅ Frame extraction complete: {extracted_count} frames extracted")

            return {
                'success': True,
                'extracted_frames': extracted_count,
                'frames_dir': frames_dir
            }

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error extracting frames: {e}")
            return {
                'success': False,
                'error': str(e)
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
