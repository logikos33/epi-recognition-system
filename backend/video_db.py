"""
Video CRUD Module for EPI Recognition System

Provides video management functions for training projects.
Videos are uploaded, processed for frames, and used for annotation.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, List, Dict, Any
import uuid
import datetime
import logging

logger = logging.getLogger(__name__)


class VideoService:
    """Service for video CRUD operations"""

    @staticmethod
    def upload_video(
        db: Session,
        project_id: str,
        user_id: str,
        filename: str,
        storage_path: str,
        duration: float,
        frame_count: int,
        fps: float
    ) -> Optional[Dict[str, Any]]:
        """
        Upload a new video to a training project.

        Args:
            db: Database session
            project_id: Project UUID
            user_id: User UUID (for ownership verification)
            filename: Original filename
            storage_path: Path where video is stored
            duration: Video duration in seconds
            frame_count: Total number of frames
            fps: Frames per second

        Returns:
            Dictionary with video data or None if failed
        """
        try:
            video_id = str(uuid.uuid4())

            query = text("""
                INSERT INTO training_videos (
                    id, project_id, filename, storage_path,
                    duration_seconds, frame_count, fps, uploaded_at
                )
                VALUES (
                    :id, :project_id, :filename, :storage_path,
                    :duration, :frame_count, :fps, NOW()
                )
                RETURNING id, project_id, filename, storage_path,
                         duration_seconds, frame_count, fps, uploaded_at
            """)

            result = db.execute(query, {
                'id': video_id,
                'project_id': project_id,
                'filename': filename,
                'storage_path': storage_path,
                'duration': duration,
                'frame_count': frame_count,
                'fps': fps
            })

            db.commit()
            row = result.fetchone()

            logger.info(f"✅ Video uploaded: {filename} to project {project_id}")

            return {
                'id': str(row[0]),
                'project_id': str(row[1]),
                'filename': row[2],
                'storage_path': row[3],
                'duration_seconds': float(row[4]) if row[4] else None,
                'frame_count': row[5],
                'fps': float(row[6]) if row[6] else None,
                'uploaded_at': row[7].isoformat() if row[7] else None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error uploading video: {e}")
            raise

    @staticmethod
    def list_project_videos(
        db: Session,
        project_id: str,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """
        List all videos for a training project.

        Args:
            db: Database session
            project_id: Project UUID
            user_id: User UUID (for ownership verification)

        Returns:
            List of video dictionaries
        """
        try:
            # First verify project ownership
            project_query = text("""
                SELECT id FROM training_projects
                WHERE id = :project_id AND user_id = :user_id
            """)
            project_result = db.execute(project_query, {
                'project_id': project_id,
                'user_id': user_id
            })
            if not project_result.fetchone():
                logger.warning(f"⚠️ Project {project_id} not found for user {user_id}")
                return []

            # Get videos
            query = text("""
                SELECT id, project_id, filename, storage_path,
                       duration_seconds, frame_count, fps, uploaded_at
                FROM training_videos
                WHERE project_id = :project_id
                ORDER BY uploaded_at DESC
            """)

            result = db.execute(query, {'project_id': project_id})
            rows = result.fetchall()

            videos = []
            for row in rows:
                videos.append({
                    'id': str(row[0]),
                    'project_id': str(row[1]),
                    'filename': row[2],
                    'storage_path': row[3],
                    'duration_seconds': float(row[4]) if row[4] else None,
                    'frame_count': row[5],
                    'fps': float(row[6]) if row[6] else None,
                    'uploaded_at': row[7].isoformat() if row[7] else None
                })

            return videos

        except Exception as e:
            logger.error(f"❌ Error listing videos for project {project_id}: {e}")
            return []

    @staticmethod
    def get_video(
        db: Session,
        video_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a single video by ID.

        Args:
            db: Database session
            video_id: Video UUID
            user_id: User UUID (for ownership verification)

        Returns:
            Video dictionary or None if not found
        """
        try:
            query = text("""
                SELECT v.id, v.project_id, v.filename, v.storage_path,
                       v.duration_seconds, v.frame_count, v.fps, v.uploaded_at,
                       (SELECT COUNT(*) FROM training_frames f WHERE f.video_id = v.id) as extracted_frames
                FROM training_videos v
                JOIN training_projects p ON p.id = v.project_id
                WHERE v.id = :video_id AND p.user_id = :user_id
            """)

            result = db.execute(query, {
                'video_id': video_id,
                'user_id': user_id
            })
            row = result.fetchone()

            if row:
                return {
                    'id': str(row[0]),
                    'project_id': str(row[1]),
                    'filename': row[2],
                    'storage_path': row[3],
                    'duration_seconds': float(row[4]) if row[4] else None,
                    'frame_count': row[5],
                    'fps': float(row[6]) if row[6] else None,
                    'uploaded_at': row[7].isoformat() if row[7] else None,
                    'extracted_frames': row[8]
                }

            return None

        except Exception as e:
            logger.error(f"❌ Error fetching video {video_id}: {e}")
            return None

    @staticmethod
    def delete_video(
        db: Session,
        video_id: str,
        user_id: str
    ) -> bool:
        """
        Delete a video (cascade deletes frames and annotations).

        Args:
            db: Database session
            video_id: Video UUID
            user_id: User UUID (for ownership verification)

        Returns:
            True if successful, False otherwise
        """
        try:
            query = text("""
                DELETE FROM training_videos
                WHERE id = :video_id AND
                      project_id IN (SELECT id FROM training_projects WHERE user_id = :user_id)
                RETURNING id
            """)

            result = db.execute(query, {
                'video_id': video_id,
                'user_id': user_id
            })
            db.commit()

            deleted = result.fetchone() is not None
            if deleted:
                logger.info(f"✅ Video deleted: {video_id}")

            return deleted

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error deleting video {video_id}: {e}")
            return False

    @staticmethod
    def count_videos(db: Session, project_id: str, user_id: str) -> int:
        """
        Count videos for a project.

        Args:
            db: Database session
            project_id: Project UUID
            user_id: User UUID (for ownership verification)

        Returns:
            Number of videos
        """
        try:
            query = text("""
                SELECT COUNT(*) FROM training_videos v
                JOIN training_projects p ON p.id = v.project_id
                WHERE v.project_id = :project_id AND p.user_id = :user_id
            """)

            result = db.execute(query, {
                'project_id': project_id,
                'user_id': user_id
            })
            row = result.fetchone()

            return row[0] if row else 0

        except Exception as e:
            logger.error(f"❌ Error counting videos: {e}")
            return 0


# Export service class
__all__ = ['VideoService']
