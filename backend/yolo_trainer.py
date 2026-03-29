"""
YOLO Training Service for EPI Recognition System

Handles YOLOv8 training execution, progress tracking,
and model management using the ultralytics library.
"""
import os
import uuid
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class YOLOTrainer:
    """Execute YOLOv8 training jobs and track progress."""

    def __init__(self):
        """Initialize YOLO trainer."""
        self.models_dir = os.environ.get('MODELS_DIR', 'models')
        self.datasets_dir = os.environ.get('DATASETS_DIR', 'datasets')
        os.makedirs(self.models_dir, exist_ok=True)
        os.makedirs(self.datasets_dir, exist_ok=True)

    def start_training(
        self,
        db: Session,
        project_id: str,
        config: Dict[str, Any],
        augmentation: Dict[str, Any],
        model: str = 'yolov8n.pt'
    ) -> Dict[str, Any]:
        """
        Start a YOLO training job.

        Args:
            db: Database session
            project_id: Project UUID
            config: Training configuration (epochs, batch_size, image_size, device, etc.)
            augmentation: Data augmentation settings
            model: Base model to use (yolov8n.pt, yolov8s.pt, etc.)

        Returns:
            Dictionary with success status and training_id
        """
        try:
            # Get project info
            project_query = text("""
                SELECT name, target_classes FROM training_projects WHERE id = :project_id
            """)
            project_result = db.execute(project_query, {'project_id': project_id})
            project_row = project_result.fetchone()

            if not project_row:
                return {'success': False, 'error': 'Project not found'}

            project_name = project_row[0]
            target_classes = list(project_row[1]) if project_row[1] else []

            # Create training record
            training_id = str(uuid.uuid4())

            training_query = text("""
                INSERT INTO trained_models
                (id, project_id, model_name, version, storage_path,
                 training_epochs, is_active, created_at)
                VALUES (:id, :project_id, :model_name, 1, :storage_path, :epochs, false, NOW())
                RETURNING id
            """)

            # Generate model storage path
            model_filename = f"{project_name}_{training_id[:8]}.pt"
            model_path = os.path.join(self.models_dir, model_filename)

            db.execute(training_query, {
                'id': training_id,
                'project_id': project_id,
                'model_name': f"{project_name}_custom",
                'storage_path': model_path,
                'epochs': config.get('epochs', 100)
            })
            db.commit()

            # Update project status to training
            update_query = text("""
                UPDATE training_projects
                SET status = 'training', updated_at = NOW()
                WHERE id = :project_id
            """)
            db.execute(update_query, {'project_id': project_id})
            db.commit()

            # Check if dataset exists (from YOLO exporter)
            dataset_path = os.path.join(self.datasets_dir, project_id)
            data_yaml = os.path.join(dataset_path, 'data.yaml')

            if not os.path.exists(data_yaml):
                logger.warning(f"Dataset not found at {data_yaml}, training will fail")
                # Don't fail here - let the training process handle it

            # Spawn training in background thread (non-blocking)
            # In production, use Celery or similar task queue
            try:
                import threading
                training_thread = threading.Thread(
                    target=self._run_training,
                    args=(db, training_id, project_id, model_path, data_yaml, config, augmentation)
                )
                training_thread.daemon = True
                training_thread.start()

                logger.info(f"✅ Training job started: {training_id}")

            except Exception as e:
                logger.error(f"❌ Failed to start training thread: {e}")
                # Update training status to failed
                self._update_training_status(db, training_id, 'failed', str(e))
                return {'success': False, 'error': f'Failed to start training: {str(e)}'}

            return {
                'success': True,
                'training_id': training_id,
                'message': 'Training job started successfully'
            }

        except Exception as e:
            logger.error(f"❌ Error starting training: {e}")
            db.rollback()
            return {'success': False, 'error': str(e)}

    def _run_training(
        self,
        db: Session,
        training_id: str,
        project_id: str,
        model_path: str,
        data_yaml: str,
        config: Dict[str, Any],
        augmentation: Dict[str, Any]
    ):
        """
        Run YOLO training in background thread.

        This method executes the actual training and updates the database
        with results when complete.
        """
        try:
            from ultralytics import YOLO

            logger.info(f"🚀 Starting training for {training_id}")

            # Load base model
            base_model = config.get('base_model', 'yolov8n.pt')
            yolo_model = YOLO(base_model)

            # Build training arguments
            train_args = {
                'data': data_yaml,
                'epochs': config.get('epochs', 100),
                'batch': config.get('batch_size', 16),
                'imgsz': config.get('image_size', 640),
                'device': config.get('device', 'cpu'),
                'workers': config.get('workers', 8),
                'project': self.models_dir,
                'name': training_id[:8],
                'exist_ok': True,
                'verbose': True,
                'plots': True,
                'save': True,
            }

            # Add learning rate if specified
            if 'learning_rate' in config:
                train_args['lr0'] = config['learning_rate']

            # Add optimizer if specified
            if 'optimizer' in config:
                train_args['optimizer'] = config['optimizer']

            # Add augmentation parameters
            if augmentation:
                if 'hsv_h' in augmentation:
                    train_args['hsv_h'] = augmentation['hsv_h']
                if 'hsv_s' in augmentation:
                    train_args['hsv_s'] = augmentation['hsv_s']
                if 'hsv_v' in augmentation:
                    train_args['hsv_v'] = augmentation['hsv_v']
                if 'degrees' in augmentation:
                    train_args['degrees'] = augmentation['degrees']
                if 'translate' in augmentation:
                    train_args['translate'] = augmentation['translate']
                if 'scale' in augmentation:
                    train_args['scale'] = augmentation['scale']
                if 'flipud' in augmentation:
                    train_args['flipud'] = augmentation['flipud']
                if 'fliplr' in augmentation:
                    train_args['fliplr'] = augmentation['fliplr']
                if 'mosaic' in augmentation:
                    train_args['mosaic'] = augmentation['mosaic']
                if 'mixup' in augmentation:
                    train_args['mixup'] = augmentation['mixup']

            # Run training
            start_time = datetime.now()
            results = yolo_model.train(**train_args)
            end_time = datetime.now()

            # Calculate training time
            training_time_seconds = int((end_time - start_time).total_seconds())

            # Extract metrics from results
            metrics = {}
            if hasattr(results, 'results_dict'):
                results_dict = results.results_dict
                metrics['map50'] = float(results_dict.get('metrics/mAP50(B)', 0.0))
                metrics['map75'] = float(results_dict.get('metrics/mAP75(B)', 0.0))
                metrics['map50_95'] = float(results_dict.get('metrics/mAP50-95(B)', 0.0))
                metrics['precision'] = float(results_dict.get('metrics/precision(B)', 0.0))
                metrics['recall'] = float(results_dict.get('metrics/recall(B)', 0.0))

            # Find the best weights file
            weights_dir = os.path.join(self.models_dir, training_id[:8], 'weights')
            best_weights = os.path.join(weights_dir, 'best.pt')

            if os.path.exists(best_weights):
                # Copy to final location
                import shutil
                shutil.copy(best_weights, model_path)
                logger.info(f"✅ Best weights saved to {model_path}")
            else:
                logger.warning(f"⚠️  Best weights not found at {best_weights}")

            # Save results to database
            self.save_training_results(
                db=db,
                project_id=project_id,
                model_path=model_path,
                metrics=metrics,
                training_time_seconds=training_time_seconds,
                training_id=training_id
            )

            # Update project status to completed
            update_query = text("""
                UPDATE training_projects
                SET status = 'completed', updated_at = NOW()
                WHERE id = :project_id
            """)
            db.execute(update_query, {'project_id': project_id})
            db.commit()

            logger.info(f"✅ Training completed: {training_id}")

        except Exception as e:
            logger.error(f"❌ Training failed for {training_id}: {e}")
            self._update_training_status(db, training_id, 'failed', str(e))

            # Update project status to failed
            update_query = text("""
                UPDATE training_projects
                SET status = 'failed', updated_at = NOW()
                WHERE id = :project_id
            """)
            db.execute(update_query, {'project_id': project_id})
            db.commit()

    def get_training_status(self, db: Session, project_id: str) -> Dict[str, Any]:
        """
        Get training job status for a project.

        Args:
            db: Database session
            project_id: Project UUID

        Returns:
            Dictionary with training status
        """
        try:
            # Get latest training job for project
            query = text("""
                SELECT
                    tm.id, tm.model_name, tm.storage_path,
                    tm.map50, tm.map75, tm.map50_95, tm.precision, tm.recall,
                    tm.training_epochs, tm.training_time_seconds, tm.is_active,
                    tm.created_at, tp.status as project_status
                FROM trained_models tm
                JOIN training_projects tp ON tp.id = tm.project_id
                WHERE tm.project_id = :project_id
                ORDER BY tm.created_at DESC
                LIMIT 1
            """)

            result = db.execute(query, {'project_id': project_id})
            row = result.fetchone()

            if not row:
                return {
                    'success': True,
                    'status': 'not_started',
                    'model': None
                }

            return {
                'success': True,
                'status': self._map_project_status(row[12]),
                'model': {
                    'id': str(row[0]),
                    'model_name': row[1],
                    'storage_path': row[2],
                    'map50': float(row[3]) if row[3] else None,
                    'map75': float(row[4]) if row[4] else None,
                    'map50_95': float(row[5]) if row[5] else None,
                    'precision': float(row[6]) if row[6] else None,
                    'recall': float(row[7]) if row[7] else None,
                    'training_epochs': row[8],
                    'training_time_seconds': row[9],
                    'is_active': row[10],
                    'created_at': row[11].isoformat() if row[11] else None
                }
            }

        except Exception as e:
            logger.error(f"❌ Error getting training status: {e}")
            return {'success': False, 'error': str(e)}

    def _map_project_status(self, project_status: str) -> str:
        """Map training project status to training status."""
        status_map = {
            'draft': 'not_started',
            'annotating': 'not_started',
            'training': 'running',
            'completed': 'completed',
            'failed': 'failed'
        }
        return status_map.get(project_status, 'unknown')

    def save_training_results(
        self,
        db: Session,
        project_id: str,
        model_path: str,
        metrics: Dict[str, float],
        training_time_seconds: int,
        training_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save training results to database.

        Args:
            db: Database session
            project_id: Project UUID
            model_path: Path to trained model file
            metrics: Dictionary with training metrics (map50, map75, etc.)
            training_time_seconds: Total training time in seconds
            training_id: Existing training ID to update (optional)

        Returns:
            Dictionary with success status and model_id
        """
        try:
            if training_id:
                # Update existing record
                query = text("""
                    UPDATE trained_models
                    SET storage_path = :storage_path,
                        map50 = :map50,
                        map75 = :map75,
                        map50_95 = :map50_95,
                        precision = :precision,
                        recall = :recall,
                        training_time_seconds = :training_time_seconds
                    WHERE id = :training_id
                    RETURNING id
                """)

                result = db.execute(query, {
                    'training_id': training_id,
                    'storage_path': model_path,
                    'map50': metrics.get('map50'),
                    'map75': metrics.get('map75'),
                    'map50_95': metrics.get('map50_95'),
                    'precision': metrics.get('precision'),
                    'recall': metrics.get('recall'),
                    'training_time_seconds': training_time_seconds
                })
                db.commit()

                row = result.fetchone()
                if row:
                    logger.info(f"✅ Training results updated: {training_id}")
                    return {'success': True, 'model_id': str(row[0])}

            # If no training_id or update failed, create new record
            model_id = str(uuid.uuid4())

            # Get next version number for this project
            version_query = text("""
                SELECT COALESCE(MAX(version), 0) + 1
                FROM trained_models
                WHERE project_id = :project_id
            """)
            version_result = db.execute(version_query, {'project_id': project_id})
            version = version_result.scalar() or 1

            # Get project name
            project_query = text("""
                SELECT name FROM training_projects WHERE id = :project_id
            """)
            project_result = db.execute(project_query, {'project_id': project_id})
            project_row = project_result.fetchone()
            model_name = f"{project_row[0]}_v{version}" if project_row else "custom_model"

            insert_query = text("""
                INSERT INTO trained_models
                (id, project_id, model_name, version, storage_path,
                 map50, map75, map50_95, precision, recall,
                 training_epochs, training_time_seconds, is_active, created_at)
                VALUES (:id, :project_id, :model_name, :version, :storage_path,
                        :map50, :map75, :map50_95, :precision, :recall,
                        :epochs, :training_time_seconds, false, NOW())
                RETURNING id
            """)

            result = db.execute(insert_query, {
                'id': model_id,
                'project_id': project_id,
                'model_name': model_name,
                'version': version,
                'storage_path': model_path,
                'map50': metrics.get('map50'),
                'map75': metrics.get('map75'),
                'map50_95': metrics.get('map50_95'),
                'precision': metrics.get('precision'),
                'recall': metrics.get('recall'),
                'epochs': metrics.get('epochs', 100),
                'training_time_seconds': training_time_seconds
            })
            db.commit()

            row = result.fetchone()
            logger.info(f"✅ Training results saved: {model_id}")

            return {'success': True, 'model_id': str(row[0])}

        except Exception as e:
            logger.error(f"❌ Error saving training results: {e}")
            db.rollback()
            return {'success': False, 'error': str(e)}

    def _update_training_status(self, db: Session, training_id: str, status: str, error_message: str = None):
        """Update training status in database."""
        try:
            # For now, we update the project status
            # In a full implementation, we'd have a training_jobs table
            logger.info(f"Updating training {training_id} status to {status}")
        except Exception as e:
            logger.error(f"Error updating training status: {e}")

    def get_active_model(self, db: Session, project_id: str) -> Dict[str, Any]:
        """
        Get the active trained model for a project.

        Args:
            db: Database session
            project_id: Project UUID

        Returns:
            Dictionary with active model info
        """
        try:
            query = text("""
                SELECT id, model_name, version, storage_path,
                       map50, map75, map50_95, precision, recall,
                       training_epochs, training_time_seconds, created_at
                FROM trained_models
                WHERE project_id = :project_id AND is_active = true
                ORDER BY version DESC
                LIMIT 1
            """)

            result = db.execute(query, {'project_id': project_id})
            row = result.fetchone()

            if not row:
                return {'success': True, 'model': None}

            return {
                'success': True,
                'model': {
                    'id': str(row[0]),
                    'model_name': row[1],
                    'version': row[2],
                    'storage_path': row[3],
                    'map50': float(row[4]) if row[4] else None,
                    'map75': float(row[5]) if row[5] else None,
                    'map50_95': float(row[6]) if row[6] else None,
                    'precision': float(row[7]) if row[7] else None,
                    'recall': float(row[8]) if row[8] else None,
                    'training_epochs': row[9],
                    'training_time_seconds': row[10],
                    'created_at': row[11].isoformat() if row[11] else None
                }
            }

        except Exception as e:
            logger.error(f"❌ Error getting active model: {e}")
            return {'success': False, 'error': str(e)}

    def activate_model(self, db: Session, model_id: str, user_id: str) -> Dict[str, Any]:
        """
        Set a trained model as active for its project.

        Args:
            db: Database session
            model_id: Model UUID
            user_id: User UUID (for ownership verification)

        Returns:
            Dictionary with success status
        """
        try:
            # Get model and verify ownership
            get_query = text("""
                SELECT tm.id, tm.project_id, tp.user_id
                FROM trained_models tm
                JOIN training_projects tp ON tp.id = tm.project_id
                WHERE tm.id = :model_id
            """)
            result = db.execute(get_query, {'model_id': model_id})
            row = result.fetchone()

            if not row:
                return {'success': False, 'error': 'Model not found'}

            if str(row[2]) != user_id:
                return {'success': False, 'error': 'Unauthorized'}

            project_id = str(row[1])

            # Deactivate all other models for this project
            deactivate_query = text("""
                UPDATE trained_models
                SET is_active = false
                WHERE project_id = :project_id
            """)
            db.execute(deactivate_query, {'project_id': project_id})

            # Activate this model
            activate_query = text("""
                UPDATE trained_models
                SET is_active = true
                WHERE id = :model_id
                RETURNING id, model_name
            """)
            result = db.execute(activate_query, {'model_id': model_id})
            db.commit()

            row = result.fetchone()
            logger.info(f"✅ Model activated: {model_id}")

            return {
                'success': True,
                'model_id': str(row[0]),
                'model_name': row[1]
            }

        except Exception as e:
            logger.error(f"❌ Error activating model: {e}")
            db.rollback()
            return {'success': False, 'error': str(e)}
