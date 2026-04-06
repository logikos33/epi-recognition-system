"""Training service."""
import logging
import uuid

from backend.app.infrastructure.database.connection import db_pool

logger = logging.getLogger(__name__)


class TrainingService:

    @staticmethod
    def list_jobs(user_id: str) -> list:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM training_jobs WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def create_job(user_id: str, epochs: int = 100, batch_size: int = 16) -> dict:
        job_id = str(uuid.uuid4())
        with db_pool.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO training_jobs (id, user_id, epochs, batch_size, status)
                VALUES (%s, %s, %s, %s, 'pending')
                RETURNING *
                """,
                (job_id, user_id, epochs, batch_size),
            )
            row = dict(cur.fetchone())
        return {k: str(v) if v is not None else None for k, v in row.items()}

    @staticmethod
    def get_job(user_id: str, job_id: str) -> dict | None:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM training_jobs WHERE id = %s AND user_id = %s",
                (job_id, user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None
