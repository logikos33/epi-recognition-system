"""Custom exceptions per domain."""


class EpiMonitorError(Exception):
    """Base exception."""
    status_code = 500
    message = "Internal server error"


class AuthError(EpiMonitorError):
    status_code = 401
    message = "Authentication failed"


class ForbiddenError(EpiMonitorError):
    status_code = 403
    message = "Access forbidden"


class NotFoundError(EpiMonitorError):
    status_code = 404
    message = "Resource not found"


class ValidationError(EpiMonitorError):
    status_code = 422
    message = "Validation failed"


class ConflictError(EpiMonitorError):
    status_code = 409
    message = "Resource conflict"


class StorageError(EpiMonitorError):
    status_code = 503
    message = "Storage service unavailable"


class StreamError(EpiMonitorError):
    status_code = 503
    message = "Stream service unavailable"


class TrainingError(EpiMonitorError):
    status_code = 503
    message = "Training service unavailable"


class RTSPValidationError(ValidationError):
    message = "Invalid RTSP URL"
