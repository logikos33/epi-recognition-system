"""
Video Processing Service for YOLO Training

Handles video upload, frame extraction, and video metadata management.
"""
import os
import cv2
import uuid
import logging
import shutil
import json
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class VideoService:
    """Handle video upload and frame extraction operations."""

    def __init__(self):
        self.videos_dir = 'storage/training_videos'
        self.frames_dir = 'storage/training_frames'
        os.makedirs(self.videos_dir, exist_ok=True)
        os.makedirs(self.frames_dir, exist_ok=True)

    def save_upload(self, db: Session, user_id: str, filename: str, file_content: bytes, duration: float) -> Dict[str, Any]:
        """
        Save uploaded video file and create database record.

        Args:
            db: Database session
            user_id: User UUID
            filename: Original filename
            file_content: Video file bytes
            duration: Video duration in seconds

        Returns:
            Dictionary with video_id and metadata
        """
        try:
            video_id = str(uuid.uuid4())

            # Get or create default project for user
            project_query = text("""
                SELECT id FROM training_projects
                WHERE user_id = :user_id
                ORDER BY created_at DESC
                LIMIT 1
            """)
            project_result = db.execute(project_query, {'user_id': user_id})
            project_row = project_result.fetchone()

            # Create default project if none exists
            if not project_row:
                logger.info(f"Creating default training project for user {user_id}")
                new_project_id = str(uuid.uuid4())
                create_project_query = text("""
                    INSERT INTO training_projects
                    (id, user_id, name, description, target_classes, status, created_at, updated_at)
                    VALUES (:id, :user_id, :name, :description, CAST(:target_classes AS jsonb), 'draft', NOW(), NOW())
                    RETURNING id
                """)
                db.execute(create_project_query, {
                    'id': new_project_id,
                    'user_id': user_id,
                    'name': 'Projeto Padrão',
                    'description': 'Projeto criado automaticamente para upload de vídeos',
                    'target_classes': json.dumps([])
                })
                db.commit()
                project_id = new_project_id
            else:
                project_id = str(project_row[0])

            # Save video file
            video_path = os.path.join(self.videos_dir, video_id, filename)
            os.makedirs(os.path.dirname(video_path), exist_ok=True)

            with open(video_path, 'wb') as f:
                f.write(file_content)

            # Calculate chunks (10 min max, 1 min chunks)
            max_duration = 600  # 10 minutes
            selected_duration = min(int(duration), max_duration)
            total_chunks = (selected_duration // 60) + 1

            # Create database record
            query = text("""
                INSERT INTO training_videos
                (id, project_id, filename, storage_path, original_path, duration_seconds,
                 total_chunks, status)
                VALUES (:id, :project_id, :filename, :path, :path, :duration, :chunks, 'uploaded')
                RETURNING id, uploaded_at
            """)

            result = db.execute(query, {
                'id': video_id,
                'project_id': project_id,  # Use actual project_id
                'filename': filename,
                'path': video_path,
                'duration': int(duration),
                'chunks': total_chunks
            })
            db.commit()

            row = result.fetchone()
            logger.info(f"✅ Video uploaded: {filename} ({duration}s) to project {project_id}")

            return {
                'success': True,
                'video_id': str(row[0]),
                'filename': filename,
                'duration': int(duration),
                'total_chunks': total_chunks,
                'created_at': row[1].isoformat()  # Keep as created_at for API compatibility
            }

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Video upload error: {e}")
            return {'success': False, 'error': str(e)}

    def get_video(self, db: Session, video_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get video metadata by ID."""
        try:
            query = text("""
                SELECT v.id, v.project_id, v.filename, v.duration_seconds, v.selected_start,
                       v.selected_end, v.total_chunks, v.processed_chunks, v.frame_count,
                       v.status, v.uploaded_at
                FROM training_videos v
                INNER JOIN training_projects p ON v.project_id = p.id
                WHERE v.id = :video_id AND p.user_id = :user_id
            """)

            result = db.execute(query, {'video_id': video_id, 'user_id': user_id})
            row = result.fetchone()

            if not row:
                return None

            return {
                'id': str(row[0]),
                'user_id': str(row[1]),
                'filename': row[2],
                'duration': row[3],
                'selected_start': row[4],
                'selected_end': row[5],
                'total_chunks': row[6],
                'processed_chunks': row[7],
                'frame_count': row[8],
                'status': row[9],
                'created_at': row[10].isoformat() if row[10] else None  # API compatibility
            }

        except Exception as e:
            logger.error(f"❌ Get video error: {e}")
            return None

    def list_user_videos(self, db: Session, user_id: str) -> list:
        """List all videos for a user."""
        try:
            query = text("""
                SELECT v.id, v.filename, v.duration_seconds, v.frame_count,
                       v.processed_chunks, v.total_chunks, v.status, v.uploaded_at
                FROM training_videos v
                INNER JOIN training_projects p ON v.project_id = p.id
                WHERE p.user_id = :user_id
                ORDER BY v.uploaded_at DESC
            """)

            result = db.execute(query, {'user_id': user_id})
            rows = result.fetchall()

            return [
                {
                    'id': str(row[0]),
                    'filename': row[1],
                    'duration': row[2],
                    'frame_count': row[3],
                    'processed_chunks': row[4],
                    'total_chunks': row[5],
                    'status': row[6],
                    'created_at': row[7].isoformat() if row[7] else None  # API compatibility
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"❌ List videos error: {e}")
            return []

    def update_selection(self, db: Session, video_id: str, user_id: str,
                       start_seconds: int, end_seconds: int) -> bool:
        """Update user-selected time range for video."""
        try:
            query = text("""
                UPDATE training_videos
                SET selected_start = :start, selected_end = :end
                WHERE id = :video_id
                  AND EXISTS (
                    SELECT 1 FROM training_projects p
                    WHERE p.id = training_videos.project_id AND p.user_id = :user_id
                  )
            """)

            db.execute(query, {
                'video_id': video_id,
                'user_id': user_id,
                'start': start_seconds,
                'end': end_seconds
            })
            db.commit()

            logger.info(f"✅ Video {video_id} selection: {start}s - {end}s")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Update selection error: {e}")
            return False

    def delete_video(self, db: Session, video_id: str, user_id: str) -> bool:
        """Delete video and all associated frames."""
        try:
            # Delete frames (cascade will handle annotations)
            delete_frames_query = text("""
                DELETE FROM frames WHERE video_id = :video_id
            """)
            db.execute(delete_frames_query, {'video_id': video_id})

            # Delete video record
            delete_video_query = text("""
                DELETE FROM training_videos
                WHERE id = :video_id
                  AND EXISTS (
                    SELECT 1 FROM training_projects p
                    WHERE p.id = training_videos.project_id AND p.user_id = :user_id
                  )
                RETURNING original_path
            """)
            result = db.execute(delete_video_query, {'video_id': video_id, 'user_id': user_id})
            db.commit()

            row = result.fetchone()
            if row:
                # Delete video file
                video_dir = os.path.dirname(row[0])
                if os.path.exists(video_dir):
                    shutil.rmtree(video_dir)

                # Delete frames directory
                frames_dir = os.path.join(self.frames_dir, video_id)
                if os.path.exists(frames_dir):
                    shutil.rmtree(frames_dir)

                logger.info(f"✅ Video deleted: {video_id}")
                return True

            return False

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Delete video error: {e}")
            return False

    def start_frame_extraction(self, db: Session, video_id: str, user_id: str) -> Dict[str, Any]:
        """
        Start frame extraction in background thread.

        Extracts 2 frames per second in 1-minute chunks.

        Args:
            db: Database session
            video_id: Video UUID
            user_id: User UUID

        Returns:
            Dictionary with success status
        """
        try:
            video = self.get_video(db, video_id, user_id)
            if not video:
                return {'success': False, 'error': 'Video not found'}

            # Determine time range
            start_time = video.get('selected_start') or 0
            end_time = video.get('selected_end') or video['duration']
            duration = end_time - start_time

            if duration > 600:
                return {'success': False, 'error': 'Selection too long (max 10min)'}

            # Update status
            update_query = text("""
                UPDATE training_videos SET status = 'extracting'
                WHERE id = :video_id
            """)
            db.execute(update_query, {'video_id': video_id})
            db.commit()

            # Start extraction in background thread
            import threading
            extraction_thread = threading.Thread(
                target=self._extract_frames,
                args=(video_id, video['filename'], start_time, end_time)
            )
            extraction_thread.daemon = True
            extraction_thread.start()

            logger.info(f"✅ Frame extraction started: {video_id}")
            return {'success': True, 'message': 'Extraction started'}

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Start extraction error: {e}")
            return {'success': False, 'error': str(e)}

    def _extract_frames(self, video_id: str, filename: str, start_time: int, end_time: int):
        """
        Extract frames from video in background thread.

        Uses FFmpeg for fast extraction (5-10x faster than OpenCV).
        Processes chunks in parallel (up to 4 simultaneous).
        """
        try:
            from backend.database import SessionLocal

            db = SessionLocal()
            video_path = os.path.join(self.videos_dir, video_id, filename)
            output_dir = os.path.join(self.frames_dir, video_id)
            os.makedirs(output_dir, exist_ok=True)

            # Calculate duration and number of chunks
            start_time = float(start_time)
            end_time = float(end_time)
            duration = end_time - start_time
            total_chunks = int(duration / 60) + 1

            # Check if FFmpeg is available
            use_ffmpeg = shutil.which('ffmpeg') is not None

            if use_ffmpeg:
                logger.info(f"Using FFmpeg for extraction (video_id: {video_id})")
                total_frames = self._extract_with_ffmpeg(
                    db, video_id, video_path, output_dir,
                    start_time, duration, total_chunks
                )
            else:
                logger.info(f"FFmpeg not available, using OpenCV (video_id: {video_id})")
                total_frames = self._extract_with_opencv(
                    db, video_id, video_path, output_dir,
                    start_time, end_time, total_chunks
                )

            # Update video record
            finish_query = text("""
                UPDATE training_videos
                SET frame_count = :count, processed_chunks = :chunks, status = 'completed'
                WHERE id = :video_id
            """)
            db.execute(finish_query, {'video_id': video_id, 'count': total_frames, 'chunks': total_chunks})
            db.commit()

            logger.info(f"✅ Frame extraction complete: {video_id} ({total_frames} frames)")

        except Exception as e:
            logger.error(f"❌ Frame extraction error: {e}")
            # Update status to failed
            try:
                fail_query = text("""
                    UPDATE training_videos SET status = 'failed'
                    WHERE id = :video_id
                """)
                db.execute(fail_query, {'video_id': video_id})
                db.commit()
            except:
                pass
        finally:
            db.close()

    def _extract_with_ffmpeg(self, db: Session, video_id: str, video_path: str,
                           output_dir: str, start_time: float, duration: float,
                           total_chunks: int) -> int:
        """Extract frames using FFmpeg with parallel chunk processing."""

        def extract_chunk_ffmpeg(chunk_num: int) -> int:
            """Extract frames for a single chunk using FFmpeg."""
            chunk_start = start_time + (chunk_num * 60)
            chunk_duration = min(60, duration - (chunk_num * 60))
            chunk_dir = os.path.join(output_dir, f"chunk_{chunk_num:02d}")
            os.makedirs(chunk_dir, exist_ok=True)

            cmd = [
                'ffmpeg', '-y',
                '-ss', str(chunk_start),
                '-i', video_path,
                '-t', str(chunk_duration),
                '-vf', 'fps=2',
                '-q:v', '3',
                f'{chunk_dir}/frame_%05d.jpg'
            ]

            result = subprocess.run(cmd, capture_output=True, timeout=120)
            if result.returncode != 0:
                raise Exception(f"FFmpeg error chunk {chunk_num}: {result.stderr.decode()}")

            # Count frames and prepare bulk insert
            frame_files = sorted([f for f in os.listdir(chunk_dir) if f.endswith('.jpg')])

            # Bulk insert all frames from this chunk at once
            frames_data = []
            for frame_file in frame_files:
                frame_path = os.path.join(chunk_dir, frame_file)
                frame_number = int(frame_file.split('_')[1].split('.')[0])
                frames_data.append({
                    'id': str(uuid.uuid4()),
                    'video_id': video_id,
                    'frame_number': frame_number,
                    'chunk_number': chunk_num,
                    'path': frame_path
                })

            # Bulk insert
            if frames_data:
                bulk_insert_query = text("""
                    INSERT INTO frames (id, video_id, frame_number, chunk_number, storage_path)
                    VALUES (:id, :video_id, :frame_number, :chunk_number, :storage_path)
                """)

                for frame_data in frames_data:
                    db.execute(bulk_insert_query, frame_data)
                db.commit()

            # Update progress after chunk is complete
            self._update_progress(db, video_id, chunk_num + 1)

            return len(frames_data)

        # Process chunks in parallel (max 4 workers)
        max_workers = min(4, total_chunks)
        total_frames = 0

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(extract_chunk_ffmpeg, chunk): chunk
                      for chunk in range(total_chunks)}

            for future in as_completed(futures):
                chunk_num = futures[future]
                try:
                    frames_in_chunk = future.result()
                    total_frames += frames_in_chunk
                    logger.info(f"✅ Chunk {chunk_num} complete: {frames_in_chunk} frames")
                except Exception as e:
                    logger.error(f"❌ Chunk {chunk_num} failed: {e}")
                    raise

        return total_frames

    def _extract_with_opencv(self, db: Session, video_id: str, video_path: str,
                           output_dir: str, start_time: float, end_time: float,
                           total_chunks: int) -> int:
        """Extract frames using OpenCV (fallback method)."""
        # Open video
        cap = cv2.VideoCapture(video_path)
        fps = float(cap.get(cv2.CAP_PROP_FPS))

        # Set start position
        start_frame = int(start_time * fps)
        end_frame = int(end_time * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        frame_number = 0
        chunk_number = 0
        chunk_start_frame = start_frame
        saved_count = 0

        # Extract in 1-minute chunks
        chunk_duration_frames = int(60 * fps)
        extraction_interval = int(fps / 2)  # 2 frames per second

        while True:
            ret, frame = cap.read()
            if not ret or int(cap.get(cv2.CAP_PROP_POS_FRAMES)) > end_frame:
                break

            current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))

            # Save 2 frames per second
            if (current_frame - chunk_start_frame) % extraction_interval == 0:
                frame_filename = f"chunk_{chunk_number:02d}_frame_{saved_count:05d}.jpg"
                frame_path = os.path.join(output_dir, frame_filename)
                cv2.imwrite(frame_path, frame)

                # Save frame to database
                self._save_frame_to_db(db, video_id, frame_number, chunk_number, frame_path)
                saved_count += 1
                frame_number += 1

            # Update chunk progress
            if (current_frame - chunk_start_frame) >= chunk_duration_frames:
                chunk_number += 1
                chunk_start_frame = current_frame

                # Update processed_chunks in database
                self._update_progress(db, video_id, chunk_number + 1)

        cap.release()
        return saved_count

    def _save_frame_to_db(self, db: Session, video_id: str, frame_number: int, chunk_number: int, path: str):
        """Save frame record to database."""
        query = text("""
            INSERT INTO frames (id, video_id, frame_number, chunk_number, storage_path)
            VALUES (:id, :video_id, :frame_num, :chunk_num, :path)
        """)
        db.execute(query, {
            'id': str(uuid.uuid4()),
            'video_id': video_id,
            'frame_num': frame_number,
            'chunk_num': chunk_number,
            'path': path
        })
        db.commit()

    def _update_progress(self, db: Session, video_id: str, processed_chunks: int):
        """Update extraction progress."""
        query = text("""
            UPDATE training_videos SET processed_chunks = :chunks
            WHERE id = :video_id
        """)
        db.execute(query, {'video_id': video_id, 'chunks': processed_chunks})
        db.commit()
