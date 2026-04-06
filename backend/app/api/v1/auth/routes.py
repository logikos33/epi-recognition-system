"""Auth blueprint — register, login, logout, verify."""
import logging

from flask import Blueprint, g, request

from backend.app.api.v1.auth.service import AuthService
from backend.app.core.auth import require_auth
from backend.app.core.exceptions import AuthError, ValidationError
from backend.app.core.responses import created, error, success, unauthorized

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/api/v1/auth")


@auth_bp.post("/register")
def register():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "").strip()

    if not email or not password:
        return error("Email and password are required", 422)
    if len(password) < 6:
        return error("Password must be at least 6 characters", 422)

    try:
        result = AuthService.register(email, password, full_name)
        return created(result, "Account created successfully")
    except ValidationError as e:
        return error(str(e), 422)
    except Exception as e:
        logger.error("Registration error: %s", e)
        return error("Registration failed", 500)


@auth_bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    if not email or not password:
        return error("Email and password are required", 422)

    try:
        result = AuthService.login(email, password)
        return success(result, "Login successful")
    except AuthError as e:
        return unauthorized(str(e))
    except Exception as e:
        logger.error("Login error: %s", e)
        return error("Login failed", 500)


@auth_bp.get("/verify")
@require_auth
def verify():
    return success({"user_id": g.user_id, "email": g.current_user.get("email")}, "Token valid")


@auth_bp.post("/logout")
@require_auth
def logout():
    try:
        AuthService.logout(g.user_id)
    except Exception:
        pass  # Logout is best-effort
    return success(message="Logged out successfully")
