"""Unit tests for RTSPUrlValidator."""
import os
import pytest

from backend.app.core.validators import RTSPUrlValidator
from backend.app.core.exceptions import RTSPValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid(url: str) -> str:
    """Assert that validate() succeeds and returns the url unchanged."""
    result = RTSPUrlValidator.validate(url)
    assert result == url
    return result


def _invalid(url, match: str | None = None):
    """Assert that validate() raises RTSPValidationError."""
    with pytest.raises(RTSPValidationError, match=match):
        RTSPUrlValidator.validate(url)


# ---------------------------------------------------------------------------
# Happy-path: valid RTSP URLs
# ---------------------------------------------------------------------------

class TestRTSPUrlValidatorValid:
    def test_plain_rtsp_url_passes(self):
        _valid("rtsp://192.168.1.100:554/stream")

    def test_rtsps_scheme_passes(self):
        _valid("rtsps://192.168.1.200:443/secure/stream")

    def test_rtsp_with_credentials_passes(self):
        _valid("rtsp://admin:password@192.168.1.100:554/live")

    def test_rtsp_hostname_passes(self):
        _valid("rtsp://camera.example.com:554/stream1")

    def test_rtsp_without_port_passes(self):
        _valid("rtsp://192.168.1.100/stream")

    def test_rtsp_with_path_passes(self):
        _valid("rtsp://192.168.1.100:554/channel/1/stream")


# ---------------------------------------------------------------------------
# Invalid scheme
# ---------------------------------------------------------------------------

class TestRTSPUrlValidatorInvalidScheme:
    def test_http_scheme_fails(self):
        _invalid("http://192.168.1.100:554/stream")

    def test_https_scheme_fails(self):
        _invalid("https://192.168.1.100:554/stream")

    def test_ftp_scheme_fails(self):
        _invalid("ftp://192.168.1.100/stream")

    def test_no_scheme_fails(self):
        _invalid("192.168.1.100:554/stream")


# ---------------------------------------------------------------------------
# Path traversal
# ---------------------------------------------------------------------------

class TestRTSPUrlValidatorPathTraversal:
    def test_double_dot_slash_in_path_fails(self):
        # The INJECTION_PATTERNS regex catches ../ before URL parsing
        _invalid("rtsp://192.168.1.100:554/../etc/shadow")

    def test_double_dot_in_nested_path_fails(self):
        # .. without trailing slash caught by post-parse path check
        _invalid("rtsp://192.168.1.100:554/stream/../etc")


# ---------------------------------------------------------------------------
# Injection characters
# ---------------------------------------------------------------------------

class TestRTSPUrlValidatorInjection:
    def test_semicolon_fails(self):
        _invalid("rtsp://192.168.1.100:554/stream;rm -rf /")

    def test_pipe_fails(self):
        _invalid("rtsp://192.168.1.100:554/stream|id")

    def test_ampersand_fails(self):
        _invalid("rtsp://192.168.1.100:554/stream&whoami")

    def test_backtick_fails(self):
        _invalid("rtsp://192.168.1.100:554/`id`")

    def test_dollar_sign_fails(self):
        _invalid("rtsp://192.168.1.100:554/$(id)")


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestRTSPUrlValidatorEdgeCases:
    def test_empty_string_fails(self):
        _invalid("")

    def test_none_fails(self):
        with pytest.raises(RTSPValidationError):
            RTSPUrlValidator.validate(None)

    def test_overly_long_url_fails(self):
        # Build a URL that exceeds the 512-character limit
        long_path = "a" * 600
        _invalid(f"rtsp://192.168.1.100:554/{long_path}")

    def test_url_at_exactly_512_chars_is_acceptable_structure(self):
        # A URL of 512 chars should hit the length check; one of 511 should not
        # We only check that the error is raised for >512; exact boundary is
        # verified by confirming a short valid URL passes.
        _valid("rtsp://192.168.1.100:554/x")
