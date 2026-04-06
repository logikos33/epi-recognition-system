"""PostgreSQL connection pool using psycopg2 (NO SQLAlchemy)."""
import logging
import os
from contextlib import contextmanager

import psycopg2
import psycopg2.extras
import psycopg2.pool

logger = logging.getLogger(__name__)


class DatabasePool:
    """Thread-safe PostgreSQL connection pool."""

    def __init__(self):
        self._pool: psycopg2.pool.ThreadedConnectionPool | None = None

    def init_app(self, app=None) -> None:
        """Initialize pool from app config or env."""
        url = (
            (app.config.get("DATABASE_URL") if app else None)
            or os.environ.get("DATABASE_URL", "")
        )
        if not url:
            logger.warning("DATABASE_URL not set — database unavailable")
            return
        # Railway uses postgres:// but psycopg2 requires postgresql://
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        # Add connect_timeout to prevent hanging on startup
        if "connect_timeout" not in url:
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}connect_timeout=10"
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=url,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
            logger.info("Database pool ready (min=1, max=10)")
        except Exception as e:
            logger.error("Failed to create database pool: %s", e)
            self._pool = None

    @contextmanager
    def get_connection(self):
        """Context manager for acquiring/releasing connections."""
        if self._pool is None:
            raise RuntimeError("Database pool not initialized")
        conn = self._pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self):
        """Context manager for a database cursor."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    @property
    def is_available(self) -> bool:
        return self._pool is not None

    def close(self) -> None:
        if self._pool:
            self._pool.closeall()
            logger.info("Database pool closed")


# Global pool instance
db_pool = DatabasePool()
