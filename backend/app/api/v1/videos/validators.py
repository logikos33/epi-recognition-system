"""Video upload validation."""
from backend.app.constants import ALLOWED_VIDEO_EXTENSIONS, MAX_VIDEO_SIZE_BYTES
from backend.app.core.exceptions import ValidationError


class VideoUploadValidator:
    @staticmethod
    def validate_filename(filename: str) -> None:
        """Validate filename only (for presigned URL generation)."""
        if not filename:
            raise ValidationError("Filename required")
        ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise ValidationError(
                f"Invalid file type {ext!r}. Allowed: {sorted(ALLOWED_VIDEO_EXTENSIONS)}"
            )

    @staticmethod
    def validate(file) -> None:
        if not file or not file.filename:
            raise ValidationError("No file provided")

        filename = file.filename.lower()
        ext = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
        if ext not in ALLOWED_VIDEO_EXTENSIONS:
            raise ValidationError(
                f"Invalid file type {ext!r}. Allowed: {sorted(ALLOWED_VIDEO_EXTENSIONS)}"
            )

        # Check size if available
        file.seek(0, 2)
        size = file.tell()
        file.seek(0)
        if size > MAX_VIDEO_SIZE_BYTES:
            raise ValidationError(
                f"File too large ({size // 1024 // 1024}MB). Max: {MAX_VIDEO_SIZE_BYTES // 1024 // 1024}MB"
            )
