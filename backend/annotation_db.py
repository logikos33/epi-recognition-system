# backend/annotation_db.py
from sqlalchemy import text
from typing import List, Dict, Any, Optional
from uuid import uuid4
import cv2

class AnnotationDB:
    """Database operations for training annotations"""

    def create_annotation(
        self,
        db,
        frame_id: str,
        class_name: str,
        bbox_x: float,
        bbox_y: float,
        bbox_width: float,
        bbox_height: float,
        is_ai_generated: bool = False,
        confidence: Optional[float] = None,
        created_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new annotation for a frame"""
        annotation_id = str(uuid4())

        query = text("""
            INSERT INTO training_annotations
            (id, frame_id, class_name, bbox_x, bbox_y, bbox_width, bbox_height,
             confidence, is_ai_generated, created_by)
            VALUES
            (:id, :frame_id, :class_name, :bbox_x, :bbox_y, :bbox_width,
             :bbox_height, :confidence, :is_ai_generated, :created_by)
            RETURNING *
        """)

        result = db.execute(query, {
            'id': annotation_id,
            'frame_id': frame_id,
            'class_name': class_name,
            'bbox_x': bbox_x,
            'bbox_y': bbox_y,
            'bbox_width': bbox_width,
            'bbox_height': bbox_height,
            'confidence': confidence,
            'is_ai_generated': is_ai_generated,
            'created_by': created_by
        })
        db.commit()

        row = result.fetchone()
        return {
            'id': str(row[0]),
            'frame_id': str(row[1]),
            'class_name': row[2],
            'bbox_x': float(row[3]),
            'bbox_y': float(row[4]),
            'bbox_width': float(row[5]),
            'bbox_height': float(row[6]),
            'confidence': float(row[7]) if row[7] else None,
            'is_ai_generated': row[8],
            'is_reviewed': row[9],
            'created_at': row[10].isoformat(),
            'created_by': str(row[11]) if row[11] else None
        }

    def get_frame_annotations(self, db, frame_id: str) -> List[Dict[str, Any]]:
        """Get all annotations for a specific frame"""
        query = text("""
            SELECT
                id, frame_id, class_name, bbox_x, bbox_y, bbox_width, bbox_height,
                confidence, is_ai_generated, is_reviewed, created_at, created_by
            FROM training_annotations
            WHERE frame_id = :frame_id
            ORDER BY created_at ASC
        """)

        result = db.execute(query, {'frame_id': frame_id})
        rows = result.fetchall()

        return [
            {
                'id': str(row[0]),
                'frame_id': str(row[1]),
                'class_name': row[2],
                'bbox_x': float(row[3]),
                'bbox_y': float(row[4]),
                'bbox_width': float(row[5]),
                'bbox_height': float(row[6]),
                'confidence': float(row[7]) if row[7] else None,
                'is_ai_generated': row[8],
                'is_reviewed': row[9],
                'created_at': row[10].isoformat(),
                'created_by': str(row[11]) if row[11] else None
            }
            for row in rows
        ]

    def update_annotation(
        self,
        db,
        annotation_id: str,
        class_name: Optional[str] = None,
        bbox_x: Optional[float] = None,
        bbox_y: Optional[float] = None,
        bbox_width: Optional[float] = None,
        bbox_height: Optional[float] = None,
        is_reviewed: Optional[bool] = None
    ) -> bool:
        """Update an existing annotation"""
        # Build dynamic update query
        update_fields = []
        params = {'annotation_id': annotation_id}

        if class_name is not None:
            update_fields.append('class_name = :class_name')
            params['class_name'] = class_name

        if bbox_x is not None:
            update_fields.append('bbox_x = :bbox_x')
            params['bbox_x'] = bbox_x

        if bbox_y is not None:
            update_fields.append('bbox_y = :bbox_y')
            params['bbox_y'] = bbox_y

        if bbox_width is not None:
            update_fields.append('bbox_width = :bbox_width')
            params['bbox_width'] = bbox_width

        if bbox_height is not None:
            update_fields.append('bbox_height = :bbox_height')
            params['bbox_height'] = bbox_height

        if is_reviewed is not None:
            update_fields.append('is_reviewed = :is_reviewed')
            params['is_reviewed'] = is_reviewed

        if not update_fields:
            return False

        query = text(f"""
            UPDATE training_annotations
            SET {', '.join(update_fields)}
            WHERE id = :annotation_id
        """)

        result = db.execute(query, params)
        db.commit()

        return result.rowcount > 0

    def delete_annotation(self, db, annotation_id: str) -> bool:
        """Delete an annotation"""
        query = text("""
            DELETE FROM training_annotations
            WHERE id = :annotation_id
        """)

        result = db.execute(query, {'annotation_id': annotation_id})
        db.commit()

        return result.rowcount > 0

    def export_frame_to_yolo(self, db, frame_id: str, target_classes: List[str], image_path: str) -> Optional[str]:
        """
        Export a single frame's annotations to YOLO format.

        Returns YOLO format string or None if frame has no annotations.
        Format: class_id x_center y_center width height (all normalized 0-1)
        """
        # Get image dimensions
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            img_height, img_width = img.shape[:2]
        except Exception:
            return None

        # Get annotations
        annotations = self.get_frame_annotations(db, frame_id)

        if not annotations:
            return None

        # Convert to YOLO format
        yolo_lines = []
        for anno in annotations:
            # Get class index
            if anno['class_name'] not in target_classes:
                continue  # Skip annotations not in target classes

            class_idx = target_classes.index(anno['class_name'])

            # Convert pixel coordinates to normalized center coordinates
            # YOLO format: x_center, y_center, width, height (all normalized 0-1)
            x_center = (anno['bbox_x'] + anno['bbox_width'] / 2) / img_width
            y_center = (anno['bbox_y'] + anno['bbox_height'] / 2) / img_height
            width = anno['bbox_width'] / img_width
            height = anno['bbox_height'] / img_height

            # Clamp values to [0, 1]
            x_center = max(0.0, min(1.0, x_center))
            y_center = max(0.0, min(1.0, y_center))
            width = max(0.0, min(1.0, width))
            height = max(0.0, min(1.0, height))

            yolo_lines.append(f"{class_idx} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}")

        return '\n'.join(yolo_lines) if yolo_lines else None
