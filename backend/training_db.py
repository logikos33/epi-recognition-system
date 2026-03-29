"""
Training Database Module for EPI Recognition System

Handles database operations for training projects, videos, frames,
annotations, and trained models.
"""
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text, bindparam, JSON
from sqlalchemy.dialects.postgresql import JSONB
import uuid
import logging
import json

logger = logging.getLogger(__name__)


class TrainingProjectDB:
    """Database operations for training projects."""

    @staticmethod
    def create_project(
        db: Session,
        user_id: str,
        name: str,
        description: Optional[str] = None,
        target_classes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new training project.

        Args:
            db: Database session
            user_id: User UUID
            name: Project name
            description: Project description (optional)
            target_classes: List of target class names (e.g., ["helmet", "vest"])

        Returns:
            Dictionary with project data
        """
        try:
            project_id = str(uuid.uuid4())

            # Build the query with proper JSONB casting using bindparam
            query = text("""
                INSERT INTO training_projects
                (id, user_id, name, description, target_classes, status, created_at, updated_at)
                VALUES (:id, :user_id, :name, :description, CAST(:target_classes AS jsonb), 'draft', NOW(), NOW())
                RETURNING id, user_id, name, description, target_classes, status, created_at, updated_at
            """)

            result = db.execute(query, {
                'id': project_id,
                'user_id': user_id,
                'name': name,
                'description': description,
                'target_classes': json.dumps(target_classes or [])
            })

            db.commit()
            row = result.fetchone()

            logger.info(f"✅ Project created: {name} for user {user_id}")

            return {
                'id': str(row[0]),
                'user_id': str(row[1]),
                'name': row[2],
                'description': row[3],
                'target_classes': row[4],
                'status': row[5],
                'created_at': row[6].isoformat() if row[6] else None,
                'updated_at': row[7].isoformat() if row[7] else None
            }

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error creating project: {e}")
            raise

    @staticmethod
    def get_project(db: Session, project_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a training project by ID.

        Args:
            db: Database session
            project_id: Project UUID
            user_id: User UUID

        Returns:
            Dictionary with project data or None if not found
        """
        try:
            query = text("""
                SELECT id, user_id, name, description, target_classes, status, created_at, updated_at
                FROM training_projects
                WHERE id = :project_id AND user_id = :user_id
            """)

            result = db.execute(query, {'project_id': project_id, 'user_id': user_id})
            row = result.fetchone()

            if not row:
                return None

            return {
                'id': str(row[0]),
                'user_id': str(row[1]),
                'name': row[2],
                'description': row[3],
                'target_classes': row[4],
                'status': row[5],
                'created_at': row[6].isoformat() if row[6] else None,
                'updated_at': row[7].isoformat() if row[7] else None
            }

        except Exception as e:
            logger.error(f"❌ Error fetching project {project_id}: {e}")
            return None

    @staticmethod
    def list_user_projects(db: Session, user_id: str) -> List[Dict[str, Any]]:
        """
        List all training projects for a user.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            List of project dictionaries
        """
        try:
            query = text("""
                SELECT id, user_id, name, description, target_classes, status, created_at, updated_at
                FROM training_projects
                WHERE user_id = :user_id
                ORDER BY created_at DESC
            """)

            result = db.execute(query, {'user_id': user_id})
            rows = result.fetchall()

            return [
                {
                    'id': str(row[0]),
                    'user_id': str(row[1]),
                    'name': row[2],
                    'description': row[3],
                    'target_classes': row[4],
                    'status': row[5],
                    'created_at': row[6].isoformat() if row[6] else None,
                    'updated_at': row[7].isoformat() if row[7] else None
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"❌ Error listing projects for user {user_id}: {e}")
            return []

    @staticmethod
    def update_project(
        db: Session,
        project_id: str,
        user_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        target_classes: Optional[List[str]] = None,
        status: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update a training project.

        Args:
            db: Database session
            project_id: Project UUID
            user_id: User UUID (for ownership verification)
            name: New name (optional)
            description: New description (optional)
            target_classes: New target classes (optional)
            status: New status (optional)

        Returns:
            Updated project dictionary or None if not found
        """
        try:
            # Build update query dynamically based on provided fields
            update_fields = []
            params = {'project_id': project_id, 'user_id': user_id}

            if name is not None:
                update_fields.append("name = :name")
                params['name'] = name

            if description is not None:
                update_fields.append("description = :description")
                params['description'] = description

            if target_classes is not None:
                update_fields.append("target_classes = CAST(:target_classes AS jsonb)")
                params['target_classes'] = json.dumps(target_classes)

            if status is not None:
                update_fields.append("status = :status")
                params['status'] = status

            # Always update updated_at
            update_fields.append("updated_at = NOW()")

            query = text(f"""
                UPDATE training_projects
                SET {', '.join(update_fields)}
                WHERE id = :project_id AND user_id = :user_id
                RETURNING id, user_id, name, description, target_classes, status, created_at, updated_at
            """)

            result = db.execute(query, params)
            db.commit()
            row = result.fetchone()

            if row:
                logger.info(f"✅ Project updated: {project_id}")
                return {
                    'id': str(row[0]),
                    'user_id': str(row[1]),
                    'name': row[2],
                    'description': row[3],
                    'target_classes': row[4],
                    'status': row[5],
                    'created_at': row[6].isoformat() if row[6] else None,
                    'updated_at': row[7].isoformat() if row[7] else None
                }

            return None

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error updating project {project_id}: {e}")
            raise

    @staticmethod
    def delete_project(db: Session, project_id: str, user_id: str) -> bool:
        """
        Delete a training project.

        Args:
            db: Database session
            project_id: Project UUID
            user_id: User UUID

        Returns:
            True if deleted, False if not found
        """
        try:
            query = text("""
                DELETE FROM training_projects
                WHERE id = :project_id AND user_id = :user_id
                RETURNING id
            """)

            result = db.execute(query, {'project_id': project_id, 'user_id': user_id})
            db.commit()

            deleted = result.fetchone() is not None
            if deleted:
                logger.info(f"✅ Project deleted: {project_id}")

            return deleted

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error deleting project {project_id}: {e}")
            raise

    @staticmethod
    def update_project_status(db: Session, project_id: str, user_id: str, status: str) -> bool:
        """
        Update only the status of a training project.

        Args:
            db: Database session
            project_id: Project UUID
            user_id: User UUID (for ownership verification)
            status: New status (e.g., 'draft', 'in_progress', 'completed')

        Returns:
            True if updated, False if project not found
        """
        try:
            query = text("""
                UPDATE training_projects
                SET status = :status, updated_at = NOW()
                WHERE id = :project_id AND user_id = :user_id
            """)

            result = db.execute(query, {'project_id': project_id, 'user_id': user_id, 'status': status})
            db.commit()

            updated = result.rowcount > 0
            if updated:
                logger.info(f"✅ Project status updated: {project_id} -> {status}")

            return updated

        except Exception as e:
            db.rollback()
            logger.error(f"❌ Error updating project status {project_id}: {e}")
            raise
