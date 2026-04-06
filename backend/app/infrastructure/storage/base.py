"""Abstract storage interface."""
from abc import ABC, abstractmethod


class StorageBackend(ABC):
    @abstractmethod
    def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        """Upload data, return public/signed URL."""

    @abstractmethod
    def get_presigned_url(self, key: str, expires: int = 3600) -> str:
        """Get presigned URL for download."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete object."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Check if object exists."""
