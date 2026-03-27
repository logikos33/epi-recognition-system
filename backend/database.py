"""
Database Connection Module for EPI Recognition System

Provides SQLAlchemy connection pooling and database utilities.
"""
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
import os
from typing import Generator, Optional, List, Tuple, Any
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')

if not DATABASE_URL:
    logger.warning("⚠️  DATABASE_URL not set in environment variables")
    DATABASE_URL = 'postgresql://postgres:postgres@localhost:5432/epi_recognition'

# Create engine with connection pooling
engine = create_engine(
    DATABASE_URL,
    poolclass=QueuePool,
    pool_size=10,          # Number of connections to maintain
    max_overflow=20,       # Additional connections allowed beyond pool_size
    pool_pre_ping=True,    # Verify connections before using
    pool_recycle=3600,     # Recycle connections after 1 hour
    echo=False,            # Set to True for SQL query logging in debug mode
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency injection for getting database sessions.

    Usage in Flask:
        @app.route('/api/endpoint')
        def endpoint():
            db = next(get_db())
            try:
                # ... database operations ...
                db.commit()
                return jsonify({'success': True})
            except Exception as e:
                db.rollback()
                return jsonify({'error': str(e)}), 500
            finally:
                db.close()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.

    Usage:
        with get_db_context() as db:
            result = db.execute(text("SELECT * FROM users"))
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        db.close()


def execute_query(
    query: str,
    params: Optional[dict] = None,
    fetch: str = 'all'
) -> Optional[Any]:
    """
    Execute a raw SQL query.

    Args:
        query: SQL query string (use :param_name for parameters)
        params: Dictionary of parameters
        fetch: 'all', 'one', or None (no fetch)

    Returns:
        - fetch='all': List of result rows
        - fetch='one': Single result row or None
        - fetch=None: Result object (for INSERT/UPDATE/DELETE)

    Example:
        results = execute_query(
            "SELECT * FROM users WHERE email = :email",
            {'email': 'user@example.com'},
            fetch='all'
        )
    """
    try:
        with engine.connect() as conn:
            result = conn.execute(text(query), params or {})

            if fetch == 'all':
                rows = result.fetchall()
                # Convert to list of dicts for easier handling
                return [dict(row._mapping) for row in rows]
            elif fetch == 'one':
                row = result.fetchone()
                return dict(row._mapping) if row else None
            else:
                # For INSERT/UPDATE/DELETE, commit and return nothing
                conn.commit()
                return None

    except Exception as e:
        logger.error(f"Query execution error: {e}")
        raise


def execute_transaction(queries: List[Tuple[str, dict]]) -> bool:
    """
    Execute multiple queries in a transaction.

    Args:
        queries: List of (query_string, params) tuples

    Returns:
        True if all queries succeeded, False otherwise

    Example:
        success = execute_transaction([
            ("INSERT INTO users (email) VALUES (:email)", {'email': 'test@test.com'}),
            ("UPDATE users SET created_at = NOW() WHERE email = :email", {'email': 'test@test.com'})
        ])
    """
    try:
        with engine.begin() as conn:
            for query, params in queries:
                conn.execute(text(query), params)
        return True
    except Exception as e:
        logger.error(f"Transaction error: {e}")
        return False


def test_connection() -> bool:
    """
    Test database connection.

    Returns:
        True if connection successful, False otherwise
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("✅ Database connection successful")
        return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


def get_table_info(table_name: str) -> List[dict]:
    """
    Get column information for a table.

    Args:
        table_name: Name of the table

    Returns:
        List of column information dicts
    """
    query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = :table_name
        ORDER BY ordinal_position
    """
    return execute_query(query, {'table_name': table_name})


def init_db():
    """
    Initialize database connection and test it.
    Call this on application startup.
    """
    logger.info("🔌 Initializing database connection...")

    if test_connection():
        logger.info(f"📊 Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
        return True
    else:
        logger.error("❌ Failed to initialize database")
        return False


# Export for use in other modules
__all__ = [
    'engine',
    'SessionLocal',
    'get_db',
    'get_db_context',
    'execute_query',
    'execute_transaction',
    'test_connection',
    'get_table_info',
    'init_db',
]
