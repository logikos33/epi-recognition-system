"""Unit tests for VideoUploadValidator."""
import io
import pytest

from backend.app.api.v1.videos.validators import VideoUploadValidator
from backend.app.core.exceptions import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_file(filename: str, content: bytes = b"fake-video-data"):
    """Return a minimal file-like object that mimics a Flask FileStorage."""
    buf = io.BytesIO(content)
    buf.filename = filename
    buf.name = filename
    return buf


# ---------------------------------------------------------------------------
# Valid extensions
# ---------------------------------------------------------------------------

class TestVideoUploadValidatorValid:
    def test_mp4_file_passes(self):
        f = _make_file("recording.mp4")
        VideoUploadValidator.validate(f)  # must not raise

    def test_avi_file_passes(self):
        f = _make_file("clip.avi")
        VideoUploadValidator.validate(f)

    def test_mov_file_passes(self):
        f = _make_file("clip.mov")
        VideoUploadValidator.validate(f)

    def test_mkv_file_passes(self):
        f = _make_file("clip.mkv")
        VideoUploadValidator.validate(f)

    def test_webm_file_passes(self):
        f = _make_file("clip.webm")
        VideoUploadValidator.validate(f)

    def test_uppercase_extension_passes(self):
        # The validator lower-cases the filename before checking
        f = _make_file("RECORDING.MP4")
        VideoUploadValidator.validate(f)


# ---------------------------------------------------------------------------
# Invalid extensions
# ---------------------------------------------------------------------------

class TestVideoUploadValidatorInvalidExtension:
    def test_exe_file_raises_validation_error(self):
        f = _make_file("malware.exe")
        with pytest.raises(ValidationError):
            VideoUploadValidator.validate(f)

    def test_py_file_raises_validation_error(self):
        f = _make_file("script.py")
        with pytest.raises(ValidationError):
            VideoUploadValidator.validate(f)

    def test_txt_file_raises_validation_error(self):
        f = _make_file("notes.txt")
        with pytest.raises(ValidationError):
            VideoUploadValidator.validate(f)

    def test_no_extension_raises_validation_error(self):
        f = _make_file("videofile")
        with pytest.raises(ValidationError):
            VideoUploadValidator.validate(f)


# ---------------------------------------------------------------------------
# Missing / empty filename
# ---------------------------------------------------------------------------

class TestVideoUploadValidatorMissingFilename:
    def test_empty_filename_raises_validation_error(self):
        f = _make_file("")
        with pytest.raises(ValidationError):
            VideoUploadValidator.validate(f)

    def test_none_file_raises_validation_error(self):
        with pytest.raises(ValidationError):
            VideoUploadValidator.validate(None)

    def test_file_object_without_filename_attr_raises_validation_error(self):
        # Simulate object with no .filename attribute
        class NoFilename:
            pass
        with pytest.raises((ValidationError, AttributeError)):
            VideoUploadValidator.validate(NoFilename())
