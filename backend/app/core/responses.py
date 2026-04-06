"""Standardized JSON response helpers."""
from flask import jsonify


def success(data=None, message: str = "OK", status: int = 200):
    payload = {"success": True, "message": message}
    if data is not None:
        payload["data"] = data
    return jsonify(payload), status


def created(data=None, message: str = "Created"):
    return success(data, message, 201)


def error(message: str, status: int = 400, details=None):
    payload = {"success": False, "error": message}
    if details:
        payload["details"] = details
    return jsonify(payload), status


def not_found(resource: str = "Resource"):
    return error(f"{resource} not found", 404)


def unauthorized(message: str = "Authentication required"):
    return error(message, 401)


def forbidden(message: str = "Access forbidden"):
    return error(message, 403)


def validation_error(message: str, details=None):
    return error(message, 422, details)


def server_error(message: str = "Internal server error"):
    return error(message, 500)


def service_unavailable(service: str):
    return error(f"{service} service temporarily unavailable", 503)
