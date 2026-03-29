"""
Authentication Database Module for EPI Recognition System

Provides user authentication functions using PostgreSQL.
Replaces mock authentication with real database operations.
"""
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional, Dict, Any
import bcrypt
import uuid
import datetime
import logging

logger = logging.getLogger(__name__)


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """
    Verify password against hash.

    Args:
        password: Plain text password
        hashed: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: Optional[str] = None,
    company_name: Optional[str] = None,
    phone: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Create new user in database.

    Args:
        db: Database session
        email: User email (must be unique)
        password: Plain text password (will be hashed)
        full_name: User's full name
        company_name: User's company name
        phone: Phone number

    Returns:
        Dictionary with user data (id, email, full_name, company_name, created_at)
        or None if creation failed

    Raises:
        IntegrityError: If email already exists
    """
    try:
        user_id = str(uuid.uuid4())
        password_hash = hash_password(password)
        now = datetime.datetime.now(datetime.timezone.utc)

        query = text("""
            INSERT INTO users (id, email, password_hash, full_name, company_name, created_at)
            VALUES (:id, :email, :password_hash, :full_name, :company_name, :created_at)
            RETURNING id, email, full_name, company_name, created_at
        """)

        result = db.execute(query, {
            'id': user_id,
            'email': email.lower().strip(),
            'password_hash': password_hash,
            'full_name': full_name,
            'company_name': company_name,
            'created_at': now
        })

        db.commit()

        user_row = result.fetchone()
        logger.info(f"✅ User created: {email}")

        return {
            'id': str(user_row[0]),
            'email': user_row[1],
            'full_name': user_row[2],
            'company_name': user_row[3],
            'created_at': user_row[4].isoformat() if user_row[4] else None
        }

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error creating user: {e}")
        # Check if it's a duplicate email error
        if 'duplicate key' in str(e).lower() or 'unique constraint' in str(e).lower():
            raise ValueError("User with this email already exists")
        raise


def get_user_by_email(db: Session, email: str) -> Optional[Dict[str, Any]]:
    """
    Fetch user by email.

    Args:
        db: Database session
        email: User email

    Returns:
        Dictionary with user data or None if not found
    """
    try:
        query = text("""
            SELECT id, email, password_hash, full_name, company_name, created_at
            FROM users
            WHERE email = :email
        """)

        result = db.execute(query, {'email': email.lower().strip()})
        row = result.fetchone()

        if row:
            return {
                'id': str(row[0]),
                'email': row[1],
                'password_hash': row[2],
                'full_name': row[3],
                'company_name': row[4],
                'created_at': row[5].isoformat() if row[5] else None
            }

        return None

    except Exception as e:
        logger.error(f"❌ Error fetching user by email: {e}")
        return None


def get_user_by_id(db: Session, user_id: str) -> Optional[Dict[str, Any]]:
    """
    Fetch user by ID.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        Dictionary with user data or None if not found
    """
    try:
        query = text("""
            SELECT id, email, full_name, company_name, created_at
            FROM users
            WHERE id = :user_id
        """)

        result = db.execute(query, {'user_id': user_id})
        row = result.fetchone()

        if row:
            return {
                'id': str(row[0]),
                'email': row[1],
                'full_name': row[2],
                'company_name': row[3],
                'created_at': row[4].isoformat() if row[4] else None
            }

        return None

    except Exception as e:
        logger.error(f"❌ Error fetching user by ID: {e}")
        return None


def verify_user_credentials(db: Session, email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Verify user credentials (email + password).

    Args:
        db: Database session
        email: User email
        password: Plain text password

    Returns:
        Dictionary with user data (without password_hash) if valid, None otherwise
    """
    user = get_user_by_email(db, email)

    if not user:
        return None

    # Check if user is active
    if not user.get('is_active', True):
        logger.warning(f"⚠️  Inactive user attempted login: {email}")
        return None

    # Verify password
    if not verify_password(password, user['password_hash']):
        logger.warning(f"⚠️  Invalid password for: {email}")
        return None

    # Remove password hash from returned data
    user.pop('password_hash', None)

    return user


def update_last_login(db: Session, user_id: str) -> bool:
    """
    Update user's last login timestamp.
    NOTE: Simplified schema doesn't have last_login column, so this is a no-op.

    Args:
        db: Database session
        user_id: User UUID

    Returns:
        True (success - no-op for simplified schema)
    """
    try:
        # Simplified schema doesn't have last_login column
        # This function is kept for compatibility but does nothing
        return True

    except Exception as e:
        logger.error(f"❌ Error in update_last_login: {e}")
        return False


def create_session(
    db: Session,
    user_id: str,
    token: str,
    refresh_token: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
) -> bool:
    """
    Save JWT session to database.
    NOTE: Simplified schema only stores: id, user_id, token, expires_at

    Args:
        db: Database session
        user_id: User UUID
        token: JWT token
        refresh_token: Optional refresh token (not stored in simplified schema)
        ip_address: Client IP address (not stored in simplified schema)
        user_agent: Client user agent string (not stored in simplified schema)

    Returns:
        True if successful, False otherwise
    """
    try:
        session_id = str(uuid.uuid4())
        expires_at = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)

        query = text("""
            INSERT INTO sessions (id, user_id, token, expires_at)
            VALUES (:id, :user_id, :token, :expires_at)
        """)

        db.execute(query, {
            'id': session_id,
            'user_id': user_id,
            'token': token,
            'expires_at': expires_at
        })
        db.commit()

        logger.info(f"✅ Session created for user: {user_id}")
        return True

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error creating session: {e}")
        return False


def verify_session(db: Session, token: str) -> Optional[Dict[str, Any]]:
    """
    Verify session token and return user info.

    Args:
        db: Database session
        token: JWT token

    Returns:
        Dictionary with session and user info or None if invalid
    """
    try:
        # Get session with user info
        query = text("""
            SELECT s.id, s.user_id, s.expires_at, u.email, u.full_name, u.company_name
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = :token
              AND s.expires_at > NOW()
              AND u.is_active = TRUE
        """)

        result = db.execute(query, {'token': token})
        row = result.fetchone()

        if row:
            return {
                'session_id': str(row[0]),
                'user_id': str(row[1]),
                'email': row[3],
                'full_name': row[4],
                'company_name': row[5]
            }

        return None

    except Exception as e:
        logger.error(f"❌ Error verifying session: {e}")
        return None


def delete_session(db: Session, token: str) -> bool:
    """
    Delete session (logout).

    Args:
        db: Database session
        token: JWT token

    Returns:
        True if successful, False otherwise
    """
    try:
        query = text("DELETE FROM sessions WHERE token = :token")
        db.execute(query, {'token': token})
        db.commit()

        return True

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error deleting session: {e}")
        return False


def cleanup_expired_sessions(db: Session) -> int:
    """
    Remove expired sessions from database.

    Args:
        db: Database session

    Returns:
        Number of sessions deleted
    """
    try:
        query = text("DELETE FROM sessions WHERE expires_at < NOW()")
        result = db.execute(query)
        db.commit()

        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(f"🧹 Cleaned up {deleted_count} expired sessions")

        return deleted_count

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error cleaning up sessions: {e}")
        return 0


# Export all functions
__all__ = [
    'hash_password',
    'verify_password',
    'create_user',
    'get_user_by_email',
    'get_user_by_id',
    'verify_user_credentials',
    'update_last_login',
    'create_session',
    'verify_session',
    'delete_session',
    'cleanup_expired_sessions',
]
