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
        """Store config for lazy pool initialization (no connections at startup)."""
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
        # Store URL — pool is created lazily on first use
        self._url = url
        logger.info("Database URL configured (pool created on first use)")

    def _ensure_pool(self) -> None:
        """Create pool on first use (lazy initialization)."""
        if self._pool is not None:
            return
        if not hasattr(self, "_url") or not self._url:
            raise RuntimeError("Database not configured")
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                dsn=self._url,
                cursor_factory=psycopg2.extras.RealDictCursor,
                connect_timeout=10,
            )
            logger.info("Database pool ready (lazy init, min=1, max=10)")
        except Exception as e:
            logger.error("Failed to create database pool: %s", e)
            raise RuntimeError(f"Database connection failed: {e}") from e

    @contextmanager
    def get_connection(self):
        """Context manager for acquiring/releasing connections (lazy pool init)."""
        self._ensure_pool()
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
        """True if DATABASE_URL is configured (pool created lazily on first use)."""
        return bool(getattr(self, "_url", None))

    def close(self) -> None:
        if self._pool:
            self._pool.closeall()
            logger.info("Database pool closed")


# Global pool instance
db_pool = DatabasePool()
