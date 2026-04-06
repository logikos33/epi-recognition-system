"""Shared validators."""
import ipaddress
import os
import re
import urllib.parse

from backend.app.core.exceptions import RTSPValidationError, ValidationError


class RTSPUrlValidator:
    """Multi-layer RTSP URL security validator."""

    ALLOWED_SCHEMES = {"rtsp", "rtsps"}
    MAX_PATH_LENGTH = 256
    INJECTION_PATTERNS = re.compile(
        r"[;&|`$<>{}()\[\]\\]|\.\./"
    )

    @classmethod
    def validate(cls, url: str) -> str:
        """Validate and return sanitized RTSP URL."""
        if not url or not isinstance(url, str):
            raise RTSPValidationError("URL must be a non-empty string")

        if len(url) > 512:
            raise RTSPValidationError("URL too long")

        # Check for injection patterns BEFORE parsing
        if cls.INJECTION_PATTERNS.search(url):
            raise RTSPValidationError("URL contains invalid characters")

        try:
            parsed = urllib.parse.urlparse(url)
        except Exception:
            raise RTSPValidationError("Malformed URL")

        # Validate scheme
        if parsed.scheme not in cls.ALLOWED_SCHEMES:
            raise RTSPValidationError(f"Scheme must be rtsp/rtsps, got: {parsed.scheme}")

        # Validate host
        host = parsed.hostname
        if not host:
            raise RTSPValidationError("URL must have a valid host")

        # Reject localhost/internal unless in dev
        if host in ("localhost", "127.0.0.1", "::1"):
            env = os.environ.get("FLASK_ENV", "production")
            if env == "production":
                raise RTSPValidationError("Internal addresses not allowed in production")

        # Validate IP if provided
        try:
            ipaddress.ip_address(host)
        except ValueError:
            # It's a hostname — validate format
            if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$", host):
                raise RTSPValidationError("Invalid hostname format")

        # Validate port
        port = parsed.port
        if port is not None and not (1 <= port <= 65535):
            raise RTSPValidationError(f"Invalid port: {port}")

        # Validate path — check for traversal
        path = parsed.path or ""
        if ".." in path:
            raise RTSPValidationError("Path traversal detected")
        if len(path) > cls.MAX_PATH_LENGTH:
            raise RTSPValidationError("Path too long")

        return url


def validate_file_extension(filename: str, allowed: set) -> None:
    """Validate file extension against allowlist."""
    _, ext = os.path.splitext(filename.lower())
    if ext not in allowed:
        raise ValidationError(
            f"File type {ext!r} not allowed. Allowed: {sorted(allowed)}"
        )


def sanitize_string(value: str, max_length: int = 255) -> str:
    """Basic string sanitization."""
    if not isinstance(value, str):
        raise ValidationError("Expected a string value")
    stripped = value.strip()
    if len(stripped) > max_length:
        raise ValidationError(f"Value exceeds maximum length of {max_length}")
    return stripped
