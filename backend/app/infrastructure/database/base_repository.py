"""Base Repository with common CRUD patterns."""
import logging
import uuid
from typing import Any

from backend.app.infrastructure.database.connection import db_pool

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base class providing common DB operations."""

    table: str = ""

    @classmethod
    def _generate_id(cls) -> str:
        return str(uuid.uuid4())

    @classmethod
    def find_by_id(cls, record_id: str) -> dict | None:
        with db_pool.get_cursor() as cur:
            cur.execute(
                f"SELECT * FROM {cls.table} WHERE id = %s", (record_id,)
            )
            return cur.fetchone()

    @classmethod
    def find_all_by_user(cls, user_id: str) -> list[dict]:
        with db_pool.get_cursor() as cur:
            cur.execute(
                f"SELECT * FROM {cls.table} WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            return cur.fetchall()

    @classmethod
    def delete_by_id(cls, record_id: str) -> bool:
        with db_pool.get_cursor() as cur:
            cur.execute(
                f"DELETE FROM {cls.table} WHERE id = %s RETURNING id",
                (record_id,),
            )
            return cur.fetchone() is not None
