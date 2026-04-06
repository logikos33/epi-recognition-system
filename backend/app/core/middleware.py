"""Global middleware: logging, error handlers."""
import logging
import time

from flask import Flask, g, request

from backend.app.core.exceptions import EpiMonitorError
from backend.app.core.responses import error, server_error

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask) -> None:
    """Register global error handlers."""

    @app.before_request
    def before_request():
        g.start_time = time.time()

    @app.after_request
    def after_request(response):
        duration = time.time() - getattr(g, "start_time", time.time())
        logger.debug(
            "%s %s %s %.3fs",
            request.method,
            request.path,
            response.status_code,
            duration,
        )
        return response

    @app.errorhandler(EpiMonitorError)
    def handle_domain_error(e: EpiMonitorError):
        logger.warning("Domain error [%s]: %s", type(e).__name__, e)
        return error(str(e) or e.message, e.status_code)

    @app.errorhandler(404)
    def handle_404(e):
        return error("Endpoint not found", 404)

    @app.errorhandler(405)
    def handle_405(e):
        return error("Method not allowed", 405)

    @app.errorhandler(413)
    def handle_413(e):
        return error("File too large", 413)

    @app.errorhandler(500)
    def handle_500(e):
        logger.error("Unhandled error: %s", e, exc_info=True)
        return server_error()
