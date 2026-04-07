"""Annotation dataset versioning Celery tasks.

Pipeline:
    Annotated frames -> split 70/20/10 -> YOLO format labels -> R2 upload -> dataset_version record
"""
import json
import logging
import os
import tempfile
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_celery():
    try:
        from backend.app.infrastructure.queue.celery_app import get_celery
        return get_celery()
    except Exception:
        return None


def dispatch_build_dataset_version(user_id: str) -> dict:
    """Dispatch dataset versioning task (async if Celery available)."""
    celery = _get_celery()
    if celery and _build_dataset_task is not None:
        result = _build_dataset_task.apply_async(
            args=[user_id],
            queue="versioning",
        )
        return {"status": "queued", "task_id": result.id}
    else:
        logger.warning("Celery unavailable — dataset versioning deferred")
        return {"status": "degraded", "message": "Configure Redis+Celery for async versioning"}


def _annotation_to_yolo(annotation: dict, img_width: int = 1, img_height: int = 1) -> str:
    """Convert annotation dict to YOLO format line: class_index x_center y_center width height"""
    # YOLO format uses normalized coordinates (0.0-1.0)
    class_idx = annotation.get("yolo_index", 0)
    x = float(annotation.get("x_center", 0))
    y = float(annotation.get("y_center", 0))
    w = float(annotation.get("width", 0))
    h = float(annotation.get("height", 0))
    return f"{class_idx} {x:.6f} {y:.6f} {w:.6f} {h:.6f}"


def _get_next_version(user_id: str, db_pool) -> str:
    """Get next semantic version string for dataset."""
    try:
        with db_pool.get_cursor() as cur:
            # Check if dataset_versions table exists
            cur.execute("""
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables
                    WHERE table_name = 'dataset_versions'
                )
            """)
            if not cur.fetchone()["exists"]:
                return "1.0.0"
            cur.execute(
                "SELECT version FROM dataset_versions WHERE user_id = %s ORDER BY created_at DESC LIMIT 1",
                (user_id,),
            )
            row = cur.fetchone()
            if not row:
                return "1.0.0"
            # Increment patch version
            parts = row["version"].split(".")
            if len(parts) == 3:
                major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
                return f"{major}.{minor}.{patch + 1}"
    except Exception:
        pass
    return "1.0.0"


# Register Celery task if available
try:
    from backend.app.infrastructure.queue.celery_app import create_celery
    _celery = create_celery()

    if _celery:
        @_celery.task(name="annotations.build_dataset", queue="versioning", bind=True, max_retries=2)
        def _build_dataset_task(self, user_id: str):
            """Build a versioned YOLO dataset from all annotated frames."""
            from backend.app.infrastructure.database.connection import db_pool

            version = _get_next_version(user_id, db_pool)
            version_id = str(uuid.uuid4())

            # Fetch all annotated frames with their annotations and class yolo_index
            try:
                with db_pool.get_cursor() as cur:
                    cur.execute("""
                        SELECT
                            f.id as frame_id,
                            f.storage_key as frame_key,
                            f.video_id,
                            a.id as annotation_id,
                            a.x_center, a.y_center, a.width, a.height,
                            COALESCE(c.yolo_index, 0) as yolo_index
                        FROM training_frames f
                        JOIN frame_annotations a ON a.frame_id = f.id
                        LEFT JOIN yolo_classes c ON c.id = a.class_id
                        WHERE f.user_id = %s AND f.is_annotated = TRUE
                        ORDER BY f.video_id, f.frame_number
                    """, (user_id,))
                    rows = cur.fetchall()
            except Exception as e:
                logger.error("Failed to fetch annotations: %s", e)
                return {"status": "error", "error": str(e)}

            if not rows:
                logger.warning("No annotated frames found for user %s", user_id)
                return {"status": "skipped", "reason": "no annotated frames"}

            # Group annotations by frame
            frames: dict = {}
            for row in rows:
                fid = row["frame_id"]
                if fid not in frames:
                    frames[fid] = {"key": row["frame_key"], "annotations": []}
                frames[fid]["annotations"].append(dict(row))

            frame_ids = list(frames.keys())
            total = len(frame_ids)

            # Split 70/20/10
            train_end = int(total * 0.70)
            val_end = int(total * 0.90)
            splits = {
                "train": frame_ids[:train_end],
                "val": frame_ids[train_end:val_end],
                "test": frame_ids[val_end:],
            }

            # Get R2 storage if available
            try:
                from backend.app.infrastructure.storage.r2_storage import R2Storage
                account_id = os.environ.get("R2_ACCOUNT_ID", "")
                access_key = os.environ.get("R2_ACCESS_KEY_ID", "")
                secret_key = os.environ.get("R2_SECRET_ACCESS_KEY", "")
                bucket = os.environ.get("R2_BUCKET_NAME", "epi-monitor")
                endpoint = os.environ.get("R2_ENDPOINT_URL", "")
                storage = R2Storage(account_id, access_key, secret_key, bucket, endpoint) if (account_id and access_key) else None
            except Exception:
                storage = None

            label_count = 0

            with tempfile.TemporaryDirectory() as tmpdir:
                # Write label files
                for split_name, split_frame_ids in splits.items():
                    for frame_id in split_frame_ids:
                        frame_data = frames[frame_id]
                        annotations = frame_data["annotations"]
                        label_lines = [_annotation_to_yolo(a) for a in annotations]
                        label_content = "\n".join(label_lines) + "\n" if label_lines else ""

                        label_path = Path(tmpdir) / f"{frame_id}.txt"
                        label_path.write_text(label_content)

                        # Upload label to R2
                        if storage and label_content:
                            r2_key = f"datasets/v{version}/{split_name}/labels/{frame_id}.txt"
                            try:
                                storage.upload(r2_key, label_content.encode(), "text/plain")
                                label_count += 1
                            except Exception as e:
                                logger.debug("Label upload failed: %s", e)

                # Generate dataset.yaml
                yaml_content = f"""# EPI Monitor Dataset v{version}
path: datasets/v{version}
train: train/images
val: val/images
test: test/images

nc: 1
names: ['epi']
"""
                if storage:
                    try:
                        storage.upload(
                            f"datasets/v{version}/dataset.yaml",
                            yaml_content.encode(),
                            "text/yaml",
                        )
                    except Exception as e:
                        logger.debug("YAML upload failed: %s", e)

            # Generate metadata
            metadata = {
                "version": version,
                "total_frames": total,
                "splits": {k: len(v) for k, v in splits.items()},
                "labels_uploaded": label_count,
            }

            # Insert dataset_version record (graceful if table doesn't exist)
            try:
                with db_pool.get_cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS dataset_versions (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            user_id UUID NOT NULL,
                            version TEXT NOT NULL,
                            metadata JSONB,
                            r2_prefix TEXT,
                            created_at TIMESTAMPTZ DEFAULT NOW()
                        )
                    """)
                    cur.execute("""
                        INSERT INTO dataset_versions (id, user_id, version, metadata, r2_prefix)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        version_id, user_id, version,
                        json.dumps(metadata),
                        f"datasets/v{version}/",
                    ))
            except Exception as e:
                logger.warning("dataset_versions insert failed (degraded): %s", e)

            logger.info("Dataset v%s built: %s", version, metadata)
            return {"status": "ok", "version": version, **metadata}
    else:
        _build_dataset_task = None

except Exception as e:
    logger.warning("Celery task registration skipped: %s", e)
    _build_dataset_task = None
