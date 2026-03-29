"""
Camera Service for Fueling Monitoring System

Handles CRUD operations for IP cameras in fueling bays.
"""
from sqlalchemy import text
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class CameraService:
    """Service for managing IP cameras"""

    @staticmethod
    def create_camera(
        db,
        bay_id: int,
        name: str,
        rtsp_url: str = None,
        is_active: bool = True,
        position_order: int = 0
    ) -> Optional[Dict]:
        """
        Create a new camera.

        Returns:
            Camera dict or None if failed
        """
        try:
            query = text("""
                INSERT INTO cameras (bay_id, name, rtsp_url, is_active, position_order)
                VALUES (:bay_id, :name, :rtsp_url, :is_active, :position_order)
                RETURNING *
            """)
            result = db.execute(query, {
                'bay_id': bay_id,
                'name': name,
                'rtsp_url': rtsp_url,
                'is_active': is_active,
                'position_order': position_order
            })
            db.commit()
            row = result.fetchone()

            logger.info(f"✅ Created camera: {name}")
            return {
                'id': row[0],
                'bay_id': row[1],
                'name': row[2],
                'rtsp_url': row[3],
                'is_active': row[4],
                'position_order': row[5],
                'created_at': row[6].isoformat()
            }

        except Exception as e:
            logger.error(f"❌ Failed to create camera: {e}")
            db.rollback()
            return None

    @staticmethod
    def list_cameras(db) -> List[Dict]:
        """
        List all cameras.

        Returns:
            List of camera dicts
        """
        try:
            query = text("""
                SELECT c.*, b.name as bay_name
                FROM cameras c
                LEFT JOIN bays b ON c.bay_id = b.id
                ORDER BY c.position_order, c.id
            """)
            result = db.execute(query)
            rows = result.fetchall()

            cameras = []
            for row in rows:
                cameras.append({
                    'id': row[0],
                    'bay_id': row[1],
                    'name': row[2],
                    'rtsp_url': row[3],
                    'is_active': row[4],
                    'position_order': row[5],
                    'created_at': row[6].isoformat() if row[6] else None,
                    'bay_name': row[7] if len(row) > 7 else None
                })

            return cameras

        except Exception as e:
            logger.error(f"❌ Failed to list cameras: {e}")
            return []

    @staticmethod
    def get_camera_by_id(db, camera_id: int) -> Optional[Dict]:
        """
        Get camera by ID.

        Returns:
            Camera dict or None
        """
        try:
            query = text("""
                SELECT c.*, b.name as bay_name
                FROM cameras c
                LEFT JOIN bays b ON c.bay_id = b.id
                WHERE c.id = :camera_id
            """)
            result = db.execute(query, {'camera_id': camera_id})
            row = result.fetchone()

            if not row:
                return None

            return {
                'id': row[0],
                'bay_id': row[1],
                'name': row[2],
                'rtsp_url': row[3],
                'is_active': row[4],
                'position_order': row[5],
                'created_at': row[6].isoformat() if row[6] else None,
                'bay_name': row[7] if len(row) > 7 else None
            }

        except Exception as e:
            logger.error(f"❌ Failed to get camera {camera_id}: {e}")
            return None

    @staticmethod
    def update_camera(
        db,
        camera_id: int,
        name: str = None,
        rtsp_url: str = None,
        is_active: bool = None,
        position_order: int = None
    ) -> Optional[Dict]:
        """
        Update camera details.

        Returns:
            Updated camera dict or None
        """
        try:
            # Build dynamic UPDATE query
            update_fields = []
            params = {'camera_id': camera_id}

            if name is not None:
                update_fields.append("name = :name")
                params['name'] = name

            if rtsp_url is not None:
                update_fields.append("rtsp_url = :rtsp_url")
                params['rtsp_url'] = rtsp_url

            if is_active is not None:
                update_fields.append("is_active = :is_active")
                params['is_active'] = is_active

            if position_order is not None:
                update_fields.append("position_order = :position_order")
                params['position_order'] = position_order

            if not update_fields:
                return CameraService.get_camera_by_id(db, camera_id)

            query = text(f"""
                UPDATE cameras
                SET {', '.join(update_fields)}
                WHERE id = :camera_id
                RETURNING *
            """)
            result = db.execute(query, params)
            db.commit()
            row = result.fetchone()

            logger.info(f"✅ Updated camera {camera_id}")
            return {
                'id': row[0],
                'bay_id': row[1],
                'name': row[2],
                'rtsp_url': row[3],
                'is_active': row[4],
                'position_order': row[5],
                'created_at': row[6].isoformat() if row[6] else None
            }

        except Exception as e:
            logger.error(f"❌ Failed to update camera {camera_id}: {e}")
            db.rollback()
            return None

    @staticmethod
    def delete_camera(db, camera_id: int) -> bool:
        """
        Delete camera by ID.

        Returns:
            True if deleted, False otherwise
        """
        try:
            query = text("DELETE FROM cameras WHERE id = :camera_id")
            result = db.execute(query, {'camera_id': camera_id})
            db.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"✅ Deleted camera {camera_id}")
            else:
                logger.warning(f"⚠️ Camera {camera_id} not found")

            return deleted

        except Exception as e:
            logger.error(f"❌ Failed to delete camera {camera_id}: {e}")
            db.rollback()
            return False

    @staticmethod
    def get_cameras_by_bay(db, bay_id: int) -> List[Dict]:
        """
        Get all cameras for a specific bay.

        Returns:
            List of camera dicts
        """
        try:
            query = text("""
                SELECT * FROM cameras
                WHERE bay_id = :bay_id
                ORDER BY position_order, id
            """)
            result = db.execute(query, {'bay_id': bay_id})
            rows = result.fetchall()

            cameras = []
            for row in rows:
                cameras.append({
                    'id': row[0],
                    'bay_id': row[1],
                    'name': row[2],
                    'rtsp_url': row[3],
                    'is_active': row[4],
                    'position_order': row[5],
                    'created_at': row[6].isoformat() if row[6] else None
                })

            return cameras

        except Exception as e:
            logger.error(f"❌ Failed to get cameras for bay {bay_id}: {e}")
            return []