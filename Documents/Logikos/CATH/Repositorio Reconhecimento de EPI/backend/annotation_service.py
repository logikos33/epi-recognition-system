"""
Annotation Service for YOLO Training

Handles bounding box annotations in YOLO format.
"""
import logging
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class AnnotationService:
    """Handle frame annotation operations."""

    def get_frame_annotations(self, db: Session, frame_id: str) -> List[Dict[str, Any]]:
        """
        Get all annotations for a frame.

        Returns YOLO format: class_id, bbox_x, bbox_y, bbox_width, bbox_height (normalized 0-1)
        """
        try:
            query = text("""
                SELECT id, class_id, bbox_x, bbox_y, bbox_width, bbox_height, created_at
                FROM frame_annotations
                WHERE frame_id = :frame_id
                ORDER BY created_at ASC
            """)

            result = db.execute(query, {'frame_id': frame_id})
            rows = result.fetchall()

            return [
                {
                    'id': str(row[0]),
                    'class_id': row[1],
                    'x_center': float(row[2]),
                    'y_center': float(row[3]),
                    'width': float(row[4]),
                    'height': float(row[5]),
                    'created_at': row[6].isoformat() if row[6] else None
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"❌ Get annotations error: {e}")
            return []

    def save_annotations(self, db: Session, frame_id: str, annotations: List[Dict[str, Any]]) -> bool:
        """
        Save annotations for a frame (bulk replace).

        Args:
            db: Database session
            frame_id: Frame UUID
            annotations: List of annotations in YOLO format
                [{class_id, x_center, y_center, width, height}, ...]

        Returns:
            True if successful
        """
        try:
            import uuid

            # Delete existing annotations
            delete_query = text("""
                DELETE FROM frame_annotations WHERE frame_id = :frame_id
            """)
            db.execute(delete_query, {'frame_id': frame_id})

            # Insert new annotations
            if annotations:
                insert_query = text("""
                    INSERT INTO frame_annotations
                    (id, frame_id, class_id, bbox_x, bbox_y, bbox_width, bbox_height)
                    VALUES (:id, :frame_id, :class_id, :x_center, :y_center, :width, :height)
                """)

                for ann in annotations:
                    db.execute(insert_query, {
                        'id': str(uuid.uuid4()),
                        'frame_id': frame_id,
                        'class_id': ann['class_id'],
                        'x_center': ann['x_center'],
                        'y_center': ann['y_center'],
                        'width': ann['width'],
                        'height': ann['height']
                    })

            # Update frame annotation count and status
            update_query = text("""
                UPDATE frames
                SET annotation_count = :count,
                    is_annotated = CASE WHEN :count > 0 THEN TRUE ELSE FALSE END
                WHERE id = :frame_id
            """)
            db.execute(update_query, {
                'frame_id': frame_id,
                'count': len(annotations)
            })

            db.commit()
            logger.info(f"✅ Saved {len(annotations)} annotations for frame {frame_id}")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Save annotations error: {e}")
            return False

    def copy_annotations_from_frame(self, db: Session, frame_id: str, source_frame_id: str) -> bool:
        """
        Copy annotations from another frame.

        Args:
            db: Database session
            frame_id: Target frame UUID
            source_frame_id: Source frame UUID

        Returns:
            True if successful
        """
        try:
            import uuid

            # Get source annotations
            source_annotations = self.get_frame_annotations(db, source_frame_id)

            if not source_annotations:
                logger.info(f"Source frame {source_frame_id} has no annotations")
                return True

            # Copy to target frame (exclude id to create new records)
            annotations_to_save = [
                {
                    'class_id': ann['class_id'],
                    'x_center': ann['x_center'],
                    'y_center': ann['y_center'],
                    'width': ann['width'],
                    'height': ann['height']
                }
                for ann in source_annotations
            ]

            return self.save_annotations(db, frame_id, annotations_to_save)

        except Exception as e:
            logger.error(f"❌ Copy annotations error: {e}")
            return False

    def delete_annotation(self, db: Session, annotation_id: str) -> bool:
        """
        Delete a single annotation.

        Note: Not recommended for use - bulk replace via save_annotations is preferred.
        """
        try:
            query = text("""
                DELETE FROM frame_annotations WHERE id = :id
            """)
            db.execute(query, {'id': annotation_id})
            db.commit()
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Delete annotation error: {e}")
            return False
