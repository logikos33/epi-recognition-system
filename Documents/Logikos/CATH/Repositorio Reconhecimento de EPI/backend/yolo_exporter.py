# backend/yolo_exporter.py
import os
import shutil
import cv2
import logging
from typing import Dict, Any, List
from sqlalchemy import text
from collections import defaultdict

logger = logging.getLogger(__name__)


class YOLOExporter:
    """Export training annotations to YOLO format"""

    def export_project(
        self,
        db,
        project_id: str,
        output_dir: str,
        train_val_split: float = 0.8
    ) -> Dict[str, Any]:
        """
        Export all project annotations to YOLO format.

        Args:
            db: Database session
            project_id: Project UUID
            output_dir: Directory to save YOLO dataset
            train_val_split: Fraction of data to use for training (0-1)

        Returns:
            Dictionary with success status and metadata
        """

        # Get project info
        project_query = text("""
            SELECT name, target_classes FROM training_projects WHERE id = :project_id
        """)
        project_result = db.execute(project_query, {'project_id': project_id})
        project_row = project_result.fetchone()

        if not project_row:
            logger.error(f"Project not found: {project_id}")
            return {'success': False, 'error': 'Project not found'}

        project_name = project_row[0]
        target_classes = list(project_row[1])

        logger.info(f"Exporting project '{project_name}' with {len(target_classes)} classes")

        # Create directories
        os.makedirs(f'{output_dir}/images/train', exist_ok=True)
        os.makedirs(f'{output_dir}/images/val', exist_ok=True)
        os.makedirs(f'{output_dir}/labels/train', exist_ok=True)
        os.makedirs(f'{output_dir}/labels/val', exist_ok=True)

        # Get all annotated frames with their annotations
        frames_query = text("""
            SELECT
                f.id, f.storage_path, f.frame_number,
                a.class_name, a.bbox_x, a.bbox_y, a.bbox_width, a.bbox_height
            FROM training_frames f
            JOIN training_annotations a ON a.frame_id = f.id
            JOIN training_videos v ON v.id = f.video_id
            WHERE v.project_id = :project_id AND f.is_annotated = true
            ORDER BY f.id
        """)

        frames_result = db.execute(frames_query, {'project_id': project_id})
        frames = frames_result.fetchall()

        if not frames:
            logger.error(f"No annotated frames found for project {project_id}")
            return {'success': False, 'error': 'No annotated frames found'}

        logger.info(f"Found {len(frames)} annotation records")

        # Group frames by frame_id
        frame_annotations = defaultdict(list)
        frame_paths = {}

        for row in frames:
            frame_id = str(row[0])
            frame_paths[frame_id] = row[1]
            frame_annotations[frame_id].append({
                'class': row[3],
                'x': float(row[4]),
                'y': float(row[5]),
                'width': float(row[6]),
                'height': float(row[7])
            })

        # Get unique frame IDs
        frame_ids = list(frame_paths.keys())
        logger.info(f"Processing {len(frame_ids)} unique frames")

        # Split into train/val
        split_idx = int(len(frame_ids) * train_val_split)
        train_ids = frame_ids[:split_idx]
        val_ids = frame_ids[split_idx:]

        logger.info(f"Train set: {len(train_ids)} frames")
        logger.info(f"Val set: {len(val_ids)} frames")

        # Export frames
        exported_train = 0
        exported_val = 0

        for frame_id in train_ids:
            if self._export_frame(frame_id, frame_paths[frame_id], frame_annotations[frame_id],
                                  target_classes, output_dir, 'train'):
                exported_train += 1

        for frame_id in val_ids:
            if self._export_frame(frame_id, frame_paths[frame_id], frame_annotations[frame_id],
                                  target_classes, output_dir, 'val'):
                exported_val += 1

        # Write data.yaml
        yaml_content = f"""path: {output_dir}
train: images/train
val: images/val

nc: {len(target_classes)}
names: {target_classes}
"""

        with open(f'{output_dir}/data.yaml', 'w') as f:
            f.write(yaml_content)

        logger.info(f"✅ Export complete: {exported_train} train, {exported_val} val samples")

        return {
            'success': True,
            'train_samples': exported_train,
            'val_samples': exported_val,
            'data_yaml': f'{output_dir}/data.yaml'
        }

    def _export_frame(
        self,
        frame_id: str,
        image_path: str,
        annotations: List[Dict[str, Any]],
        target_classes: List[str],
        output_dir: str,
        split: str
    ) -> bool:
        """
        Export a single frame's image and annotations to YOLO format.

        Args:
            frame_id: Frame UUID
            image_path: Path to source image
            annotations: List of annotation dictionaries
            target_classes: List of target class names
            output_dir: Base output directory
            split: 'train' or 'val'

        Returns:
            True if successful, False otherwise
        """
        try:
            # Copy image
            dst_path = f'{output_dir}/images/{split}/{frame_id}.jpg'
            shutil.copy(image_path, dst_path)

            # Get image dimensions for normalization
            img = cv2.imread(image_path)
            if img is None:
                logger.error(f"Failed to read image: {image_path}")
                return False

            img_height, img_width = img.shape[:2]

            # Write label file
            label_path = f'{output_dir}/labels/{split}/{frame_id}.txt'

            with open(label_path, 'w') as f:
                for anno in annotations:
                    # Get class index
                    if anno['class'] not in target_classes:
                        logger.warning(f"Unknown class: {anno['class']}, skipping")
                        continue

                    class_idx = target_classes.index(anno['class'])

                    # Convert pixel coordinates to normalized center coordinates
                    # YOLO format: x_center, y_center, width, height (all normalized 0-1)
                    x_center = (anno['x'] + anno['width'] / 2) / img_width
                    y_center = (anno['y'] + anno['height'] / 2) / img_height
                    width = anno['width'] / img_width
                    height = anno['height'] / img_height

                    # Clamp values to [0, 1]
                    x_center = max(0.0, min(1.0, x_center))
                    y_center = max(0.0, min(1.0, y_center))
                    width = max(0.0, min(1.0, width))
                    height = max(0.0, min(1.0, height))

                    # Write YOLO format: class x_center y_center width height
                    f.write(f'{class_idx} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n')

            return True

        except Exception as e:
            logger.error(f"Error exporting frame {frame_id}: {e}")
            return False
