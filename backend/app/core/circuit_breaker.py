"""Circuit Breaker pattern for external services."""
import logging
import time
from enum import Enum
from threading import Lock

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"    # Normal operation
    OPEN = "open"        # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Thread-safe circuit breaker."""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._last_failure_time = 0.0
        self._lock = Lock()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.time() - self._last_failure_time > self.recovery_timeout:
                    self._state = CircuitState.HALF_OPEN
            return self._state

    def call(self, func, *args, fallback=None, **kwargs):
        """Execute function with circuit breaker protection."""
        if self.state == CircuitState.OPEN:
            logger.warning("[CIRCUIT OPEN] %s — using fallback", self.name)
            return fallback() if callable(fallback) else fallback

        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure(e)
            logger.error("[CIRCUIT] %s failed: %s", self.name, e)
            if callable(fallback):
                return fallback()
            raise

    def _on_success(self):
        with self._lock:
            self._failures = 0
            self._state = CircuitState.CLOSED

    def _on_failure(self, error):
        with self._lock:
            self._failures += 1
            self._last_failure_time = time.time()
            if self._failures >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "[CIRCUIT OPEN] %s after %d failures",
                    self.name,
                    self._failures,
                )
