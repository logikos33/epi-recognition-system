"""JWT utilities and auth decorators."""
import logging
import time
from functools import wraps

import jwt
from flask import current_app, g, request

from backend.app.core.exceptions import AuthError
from backend.app.core.responses import unauthorized

logger = logging.getLogger(__name__)

BEARER_PREFIX = "Bearer "


def decode_token(token: str) -> dict:
    """Decode and validate JWT token including expiration."""
    try:
        payload = jwt.decode(
            token,
            current_app.config["JWT_SECRET_KEY"],
            algorithms=["HS256"],
        )
        # Explicit expiration check (defense in depth)
        exp = payload.get("exp", 0)
        if exp and exp < time.time():
            raise AuthError("Token has expired")
        return payload
    except jwt.ExpiredSignatureError:
        raise AuthError("Token has expired")
    except jwt.InvalidTokenError as e:
        raise AuthError(f"Invalid token: {e}")


def create_token(user_id: str, email: str, ttl: int | None = None) -> str:
    """Create a signed JWT token."""
    now = int(time.time())
    ttl = ttl or current_app.config.get("JWT_TTL_SECONDS", 86400)
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "email": email,
        "iat": now,
        "exp": now + ttl,
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def get_token_from_header() -> str | None:
    """Extract Bearer token from Authorization header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith(BEARER_PREFIX):
        return auth_header[len(BEARER_PREFIX):]
    return None


def require_auth(f):
    """Decorator: require valid JWT token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_from_header()
        if not token:
            return unauthorized("Authorization token required")
        try:
            g.current_user = decode_token(token)
            g.user_id = g.current_user.get("user_id") or g.current_user.get("sub")
        except AuthError as e:
            return unauthorized(str(e))
        return f(*args, **kwargs)
    return decorated
