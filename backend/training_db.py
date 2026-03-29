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

    def create_project(
        self,
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

    def get_project_by_id(self, db: Session, project_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a training project by ID.

        Args:
            db: Database session
            project_id: Project UUID

        Returns:
            Dictionary with project data or None if not found
        """
        query = text("""
            SELECT id, user_id, name, description, target_classes, status, created_at, updated_at
            FROM training_projects
            WHERE id = :project_id
        """)

        result = db.execute(query, {'project_id': project_id})
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

    def list_projects(self, db: Session, user_id: str) -> List[Dict[str, Any]]:
        """
        List all training projects for a user.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            List of project dictionaries
        """
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

    def update_project(
        self,
        db: Session,
        project_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        target_classes: Optional[List[str]] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update a training project.

        Args:
            db: Database session
            project_id: Project UUID
            name: New name (optional)
            description: New description (optional)
            target_classes: New target classes (optional)
            status: New status (optional)

        Returns:
            Updated project dictionary
        """
        # Build update query dynamically based on provided fields
        update_fields = []
        params = {'project_id': project_id}

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
            WHERE id = :project_id
            RETURNING id, user_id, name, description, target_classes, status, created_at, updated_at
        """)

        result = db.execute(query, params)
        db.commit()
        row = result.fetchone()

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

    def delete_project(self, db: Session, project_id: str) -> bool:
        """
        Delete a training project.

        Args:
            db: Database session
            project_id: Project UUID

        Returns:
            True if deleted, False if not found
        """
        query = text("""
            DELETE FROM training_projects
            WHERE id = :project_id
            RETURNING id
        """)

        result = db.execute(query, {'project_id': project_id})
        db.commit()

        return result.fetchone() is not None
