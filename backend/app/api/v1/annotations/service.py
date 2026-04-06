"""Annotation service."""
import logging
import uuid

from backend.app.infrastructure.database.connection import db_pool

logger = logging.getLogger(__name__)


class AnnotationService:

    @staticmethod
    def list_frames(user_id: str, video_id: str | None = None) -> list:
        with db_pool.get_cursor() as cur:
            if video_id:
                cur.execute(
                    "SELECT * FROM training_frames WHERE user_id = %s AND video_id = %s ORDER BY frame_number",
                    (user_id, video_id),
                )
            else:
                cur.execute(
                    "SELECT * FROM training_frames WHERE user_id = %s ORDER BY created_at DESC LIMIT 100",
                    (user_id,),
                )
            return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def get_frame(user_id: str, frame_id: str) -> dict | None:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM training_frames WHERE id = %s AND user_id = %s",
                (frame_id, user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def save_labels(user_id: str, frame_id: str, labels: list) -> None:
        with db_pool.get_connection() as conn:
            cur = conn.cursor()
            # Delete existing annotations for this frame
            cur.execute("DELETE FROM frame_annotations WHERE frame_id = %s AND user_id = %s", (frame_id, user_id))
            # Insert new ones
            for label in labels:
                cur.execute(
                    """
                    INSERT INTO frame_annotations (id, frame_id, user_id, class_id, x_center, y_center, width, height)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        str(uuid.uuid4()), frame_id, user_id,
                        label.get("class_id"),
                        label.get("x_center", 0), label.get("y_center", 0),
                        label.get("width", 0), label.get("height", 0),
                    ),
                )
            # Mark frame as annotated
            cur.execute(
                "UPDATE training_frames SET is_annotated = TRUE WHERE id = %s AND user_id = %s",
                (frame_id, user_id),
            )

    @staticmethod
    def list_classes(user_id: str) -> list:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM yolo_classes WHERE user_id = %s ORDER BY created_at",
                (user_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def create_class(user_id: str, name: str, color: str) -> dict:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "INSERT INTO yolo_classes (id, user_id, name, color) VALUES (%s, %s, %s, %s) RETURNING *",
                (str(uuid.uuid4()), user_id, name, color),
            )
            return dict(cur.fetchone())
