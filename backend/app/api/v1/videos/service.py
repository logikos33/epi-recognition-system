"""Video service."""
import logging
import uuid

from backend.app.infrastructure.database.connection import db_pool

logger = logging.getLogger(__name__)


class VideoService:

    @staticmethod
    def list_videos(user_id: str) -> list:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "SELECT id, filename, status, frame_count, created_at FROM training_videos WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def create_upload(user_id: str, file) -> dict:
        video_id = str(uuid.uuid4())
        filename = file.filename or "upload.mp4"

        with db_pool.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO training_videos (id, user_id, filename, status)
                VALUES (%s, %s, %s, 'uploaded')
                RETURNING id, filename, status, created_at
                """,
                (video_id, user_id, filename),
            )
            row = dict(cur.fetchone())

        return {k: str(v) for k, v in row.items()}

    @staticmethod
    def get_video(user_id: str, video_id: str) -> dict | None:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM training_videos WHERE id = %s AND user_id = %s",
                (video_id, user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def delete_video(user_id: str, video_id: str) -> None:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "DELETE FROM training_videos WHERE id = %s AND user_id = %s",
                (video_id, user_id),
            )
