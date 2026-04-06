"""Auth service — bcrypt password hashing, JWT creation."""
import logging
import uuid

import bcrypt

from backend.app.core.auth import create_token
from backend.app.core.exceptions import AuthError, ValidationError
from backend.app.infrastructure.database.connection import db_pool

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def register(email: str, password: str, full_name: str = "") -> dict:
        """Register a new user."""
        # Check existing
        with db_pool.get_cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                raise ValidationError("Email already registered")

        # Hash password
        pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        user_id = str(uuid.uuid4())

        with db_pool.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (id, email, password_hash, full_name)
                VALUES (%s, %s, %s, %s)
                RETURNING id, email, full_name, created_at
                """,
                (user_id, email, pw_hash, full_name),
            )
            user = dict(cur.fetchone())

        token = create_token(str(user["id"]), user["email"])
        return {"token": token, "user": {k: str(v) for k, v in user.items()}}

    @staticmethod
    def login(email: str, password: str) -> dict:
        """Authenticate user and return JWT."""
        with db_pool.get_cursor() as cur:
            cur.execute(
                "SELECT id, email, password_hash, full_name, is_active FROM users WHERE email = %s",
                (email,),
            )
            user = cur.fetchone()

        if not user:
            raise AuthError("Invalid email or password")
        if not user["is_active"]:
            raise AuthError("Account is deactivated")

        if not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            raise AuthError("Invalid email or password")

        token = create_token(str(user["id"]), user["email"])
        return {
            "token": token,
            "user": {
                "id": str(user["id"]),
                "email": user["email"],
                "full_name": user["full_name"],
            },
        }

    @staticmethod
    def logout(user_id: str) -> None:
        """Invalidate sessions for user."""
        try:
            with db_pool.get_cursor() as cur:
                cur.execute(
                    "DELETE FROM sessions WHERE user_id = %s",
                    (user_id,),
                )
        except Exception as e:
            logger.warning("Logout DB cleanup failed: %s", e)
