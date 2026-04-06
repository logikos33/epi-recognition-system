"""Cloudflare R2 storage with circuit breaker."""
import logging

import boto3
import botocore.exceptions

from backend.app.core.circuit_breaker import CircuitBreaker
from backend.app.core.exceptions import StorageError
from backend.app.infrastructure.storage.base import StorageBackend

logger = logging.getLogger(__name__)


class R2Storage(StorageBackend):
    """Cloudflare R2 (S3-compatible) storage."""

    def __init__(self, account_id: str, access_key: str, secret_key: str, bucket: str, endpoint_url: str):
        self._bucket = bucket
        self._circuit = CircuitBreaker("R2Storage", failure_threshold=3, recovery_timeout=30)
        try:
            self._client = boto3.client(
                "s3",
                endpoint_url=endpoint_url or f"https://{account_id}.r2.cloudflarestorage.com",
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name="auto",
            )
        except Exception as e:
            logger.warning("R2 client init failed: %s", e)
            self._client = None

    def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        def _upload():
            self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)
            return key

        result = self._circuit.call(_upload, fallback=lambda: None)
        if result is None:
            raise StorageError("Upload failed — storage unavailable")
        return result

    def get_presigned_url(self, key: str, expires: int = 3600) -> str:
        def _presign():
            return self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires,
            )
        return self._circuit.call(_presign, fallback=lambda: "")

    def delete(self, key: str) -> None:
        def _delete():
            self._client.delete_object(Bucket=self._bucket, Key=key)
        self._circuit.call(_delete, fallback=lambda: None)

    def exists(self, key: str) -> bool:
        def _exists():
            self._client.head_object(Bucket=self._bucket, Key=key)
            return True
        return bool(self._circuit.call(_exists, fallback=lambda: False))
