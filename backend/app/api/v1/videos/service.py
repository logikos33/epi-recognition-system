"""Video service."""
import logging
import uuid

from backend.app.infrastructure.database.connection import db_pool

logger = logging.getLogger(__name__)


class VideoService:

    @staticmethod
    def list_videos(user_id: str) -> list:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "SELECT id, filename, status, frame_count, created_at FROM training_videos WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            rows = cur.fetchall()
            return [dict(r) for r in rows]

    @staticmethod
    def create_upload(user_id: str, file) -> dict:
        video_id = str(uuid.uuid4())
        filename = file.filename or "upload.mp4"

        with db_pool.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO training_videos (id, user_id, filename, status)
                VALUES (%s, %s, %s, 'uploaded')
                RETURNING id, filename, status, created_at
                """,
                (video_id, user_id, filename),
            )
            row = dict(cur.fetchone())

        return {k: str(v) for k, v in row.items()}

    @staticmethod
    def get_video(user_id: str, video_id: str) -> dict | None:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "SELECT * FROM training_videos WHERE id = %s AND user_id = %s",
                (video_id, user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def delete_video(user_id: str, video_id: str) -> None:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "DELETE FROM training_videos WHERE id = %s AND user_id = %s",
                (video_id, user_id),
            )

    @staticmethod
    def generate_upload_url(user_id: str, filename: str) -> dict:
        """Generate presigned PUT URL for direct upload to R2."""
        import os
        from backend.app.api.v1.videos.validators import VideoUploadValidator

        # Validate extension
        VideoUploadValidator.validate_filename(filename)

        video_id = str(uuid.uuid4())
        ext = os.path.splitext(filename)[1].lower() or ".mp4"
        storage_key = f"raw-videos/{user_id}/{video_id}{ext}"

        # Create DB record first (status=uploaded)
        with db_pool.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO training_videos (id, user_id, filename, storage_key, status)
                VALUES (%s, %s, %s, %s, 'uploaded')
                RETURNING id, filename, status, created_at
                """,
                (video_id, user_id, filename, storage_key),
            )
            row = dict(cur.fetchone())

        # Get presigned URL (may be None if R2 not configured)
        upload_url = None
        try:
            import boto3
            from backend.app.infrastructure.storage.r2_storage import R2Storage
            account_id = os.environ.get("R2_ACCOUNT_ID", "")
            access_key = os.environ.get("R2_ACCESS_KEY_ID", "")
            secret_key = os.environ.get("R2_SECRET_ACCESS_KEY", "")
            bucket = os.environ.get("R2_BUCKET_NAME", "epi-monitor")
            endpoint = os.environ.get("R2_ENDPOINT_URL", "")
            if account_id and access_key and secret_key:
                client = boto3.client(
                    "s3",
                    endpoint_url=endpoint or f"https://{account_id}.r2.cloudflarestorage.com",
                    aws_access_key_id=access_key,
                    aws_secret_access_key=secret_key,
                    region_name="auto",
                )
                upload_url = client.generate_presigned_url(
                    "put_object",
                    Params={"Bucket": bucket, "Key": storage_key, "ContentType": "video/mp4"},
                    ExpiresIn=3600,
                )
        except Exception as e:
            logger.warning("Presigned URL generation failed (degraded): %s", e)

        return {
            "video_id": str(row["id"]),
            "filename": row["filename"],
            "storage_key": storage_key,
            "upload_url": upload_url,
            "status": row["status"],
        }

    @staticmethod
    def trigger_extraction(video_id: str) -> dict:
        """Dispatch frame extraction task for a video."""
        from backend.app.api.v1.videos.tasks import dispatch_extract_frames
        from backend.app.core.exceptions import NotFoundError

        with db_pool.get_cursor() as cur:
            cur.execute("SELECT storage_key FROM training_videos WHERE id = %s", (video_id,))
            row = cur.fetchone()
        if not row:
            raise NotFoundError("Video not found")
        return dispatch_extract_frames(video_id, row["storage_key"] or "")
