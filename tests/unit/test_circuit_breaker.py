"""Unit tests for CircuitBreaker."""
import time
import pytest

from backend.app.core.circuit_breaker import CircuitBreaker, CircuitState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _raise(exc_type=RuntimeError):
    """Return a callable that always raises exc_type."""
    def _fn(*args, **kwargs):
        raise exc_type("boom")
    return _fn


def _return(value):
    """Return a callable that always returns value."""
    def _fn(*args, **kwargs):
        return value
    return _fn


# ---------------------------------------------------------------------------
# CLOSED state (healthy path)
# ---------------------------------------------------------------------------

class TestCircuitBreakerClosed:
    def test_successful_call_returns_result(self):
        cb = CircuitBreaker("test-cb", failure_threshold=3)
        result = cb.call(_return(42))
        assert result == 42

    def test_circuit_stays_closed_after_success(self):
        cb = CircuitBreaker("test-cb", failure_threshold=3)
        cb.call(_return("ok"))
        assert cb.state == CircuitState.CLOSED

    def test_single_failure_does_not_open_circuit(self):
        cb = CircuitBreaker("test-cb", failure_threshold=3)
        try:
            cb.call(_raise(), fallback=None)
        except RuntimeError:
            pass
        assert cb.state == CircuitState.CLOSED

    def test_failures_below_threshold_keep_circuit_closed(self):
        cb = CircuitBreaker("test-cb", failure_threshold=3)
        for _ in range(2):
            try:
                cb.call(_raise())
            except RuntimeError:
                pass
        assert cb.state == CircuitState.CLOSED


# ---------------------------------------------------------------------------
# OPEN state — threshold reached
# ---------------------------------------------------------------------------

class TestCircuitBreakerOpen:
    def test_n_failures_open_circuit(self):
        cb = CircuitBreaker("test-cb", failure_threshold=3)
        for _ in range(3):
            try:
                cb.call(_raise())
            except RuntimeError:
                pass
        assert cb.state == CircuitState.OPEN

    def test_open_circuit_returns_fallback_without_calling_function(self):
        cb = CircuitBreaker("test-cb", failure_threshold=2)
        # Open the circuit
        for _ in range(2):
            try:
                cb.call(_raise())
            except RuntimeError:
                pass

        call_count = {"n": 0}

        def tracked():
            call_count["n"] += 1
            return "real"

        result = cb.call(tracked, fallback="fallback-value")
        assert result == "fallback-value"
        assert call_count["n"] == 0  # function was never called

    def test_open_circuit_returns_callable_fallback_result(self):
        cb = CircuitBreaker("test-cb", failure_threshold=2)
        for _ in range(2):
            try:
                cb.call(_raise())
            except RuntimeError:
                pass

        result = cb.call(_raise(), fallback=lambda: "computed-fallback")
        assert result == "computed-fallback"


# ---------------------------------------------------------------------------
# HALF_OPEN state — recovery window
# ---------------------------------------------------------------------------

class TestCircuitBreakerHalfOpen:
    def test_circuit_transitions_to_half_open_after_recovery_timeout(self):
        cb = CircuitBreaker("test-cb", failure_threshold=2, recovery_timeout=0)
        for _ in range(2):
            try:
                cb.call(_raise())
            except RuntimeError:
                pass

        # With recovery_timeout=0 the state property should transition
        # immediately when enough time (any) has passed.
        time.sleep(0.01)
        assert cb.state == CircuitState.HALF_OPEN

    def test_success_in_half_open_closes_circuit(self):
        cb = CircuitBreaker("test-cb", failure_threshold=2, recovery_timeout=0)
        for _ in range(2):
            try:
                cb.call(_raise())
            except RuntimeError:
                pass

        # Force transition to HALF_OPEN
        time.sleep(0.01)
        assert cb.state == CircuitState.HALF_OPEN

        cb.call(_return("ok"))
        assert cb.state == CircuitState.CLOSED

    def test_failure_in_half_open_reopens_circuit(self):
        # Use a non-zero recovery_timeout so the state property does not
        # immediately flip back to HALF_OPEN after the failure sets OPEN.
        cb = CircuitBreaker("test-cb", failure_threshold=2, recovery_timeout=60)
        for _ in range(2):
            try:
                cb.call(_raise())
            except RuntimeError:
                pass

        # Manually back-date the last failure so the state property
        # transitions to HALF_OPEN on the next read.
        cb._last_failure_time = time.time() - 61
        assert cb.state == CircuitState.HALF_OPEN

        # A failure while HALF_OPEN should reopen the circuit.
        try:
            cb.call(_raise())
        except RuntimeError:
            pass
        # Immediately after the failure _last_failure_time is now() so
        # recovery_timeout=60 has NOT elapsed — state stays OPEN.
        assert cb.state == CircuitState.OPEN


# ---------------------------------------------------------------------------
# Failure counter reset
# ---------------------------------------------------------------------------

class TestCircuitBreakerFailureReset:
    def test_success_resets_failure_counter(self):
        cb = CircuitBreaker("test-cb", failure_threshold=3)
        # Two failures then one success
        for _ in range(2):
            try:
                cb.call(_raise())
            except RuntimeError:
                pass
        cb.call(_return("ok"))
        # Failures should be reset — one more failure won't open the circuit
        try:
            cb.call(_raise())
        except RuntimeError:
            pass
        assert cb.state == CircuitState.CLOSED
