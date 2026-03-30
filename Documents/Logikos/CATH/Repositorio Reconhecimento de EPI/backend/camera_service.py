"""
Camera Service for Fueling Monitoring System

Handles CRUD operations for IP cameras in fueling bays.
"""
from sqlalchemy import text
from typing import List, Dict, Optional
import logging
from backend.rtsp_builder import RTSPBuilder

logger = logging.getLogger(__name__)


class CameraService:
    """Service for managing IP cameras"""

    # IP Camera operations (ip_cameras table)

    @staticmethod
    def create_ip_camera(
        db,
        user_id: str,
        name: str,
        manufacturer: str,
        ip: str,
        port: int = 554,
        username: str = None,
        password: str = None,
        channel: int = 1,
        subtype: int = 1,
        rtsp_url: str = None,
        type: str = 'ip',
        is_active: bool = True
    ) -> Optional[Dict]:
        """
        Create a new IP camera.

        Args:
            user_id: UUID of the user creating the camera
            name: Camera name
            manufacturer: Camera manufacturer (intelbras, hikvision, generic)
            ip: Camera IP address
            port: Camera port (default 554)
            username: Optional username for authentication
            password: Optional password for authentication
            channel: Camera channel (default 1)
            subtype: Camera subtype (default 1)
            rtsp_url: Optional pre-generated RTSP URL
            type: Camera type (ip, dvr, nvr) - default 'ip'
            is_active: Whether camera is active (default True)

        Returns:
            Camera dict or None if failed
        """
        try:
            # Validate IP address format
            if not CameraService._is_valid_ip(ip):
                logger.error(f"Invalid IP address: {ip}")
                return None

            # Validate port range
            if not (1 <= port <= 65535):
                logger.error(f"Invalid port: {port}")
                return None

            # Auto-generate RTSP URL if not provided
            if not rtsp_url:
                rtsp_url = RTSPBuilder.build_url({
                    'manufacturer': manufacturer,
                    'ip': ip,
                    'port': port,
                    'username': username or '',
                    'password': password or '',
                    'channel': channel,
                    'subtype': subtype
                })

            query = text("""
                INSERT INTO ip_cameras (
                    user_id, name, manufacturer, type, ip, port,
                    username, password, channel, subtype, rtsp_url,
                    is_active
                )
                VALUES (
                    :user_id, :name, :manufacturer, :type, :ip, :port,
                    :username, :password, :channel, :subtype, :rtsp_url,
                    :is_active
                )
                RETURNING *
            """)
            result = db.execute(query, {
                'user_id': user_id,
                'name': name,
                'manufacturer': manufacturer,
                'type': type,
                'ip': ip,
                'port': port,
                'username': username,
                'password': password,
                'channel': channel,
                'subtype': subtype,
                'rtsp_url': rtsp_url,
                'is_active': is_active
            })
            db.commit()
            row = result.fetchone()

            logger.info(f"Created IP camera: {name} (ID: {row[0]})")
            return CameraService._row_to_ip_camera_dict(row)

        except Exception as e:
            logger.error(f"Failed to create IP camera: {e}")
            db.rollback()
            return None

    @staticmethod
    def list_cameras_by_user(db, user_id: str) -> List[Dict]:
        """
        List all cameras for a specific user.

        Args:
            user_id: UUID of the user

        Returns:
            List of camera dicts with password field masked
        """
        try:
            query = text("""
                SELECT * FROM ip_cameras
                WHERE user_id = :user_id
                ORDER BY created_at DESC
            """)
            result = db.execute(query, {'user_id': user_id})
            rows = result.fetchall()

            cameras = []
            for row in rows:
                camera_dict = CameraService._row_to_ip_camera_dict(row)
                cameras.append(camera_dict)

            return cameras

        except Exception as e:
            logger.error(f"Failed to list cameras for user {user_id}: {e}")
            return []

    @staticmethod
    def get_camera_by_id(db, camera_id: int) -> Optional[Dict]:
        """
        Get camera by ID (from ip_cameras table).

        Args:
            camera_id: Camera ID

        Returns:
            Camera dict or None
        """
        try:
            query = text("""
                SELECT * FROM ip_cameras
                WHERE id = :camera_id
            """)
            result = db.execute(query, {'camera_id': camera_id})
            row = result.fetchone()

            if not row:
                return None

            return CameraService._row_to_ip_camera_dict(row)

        except Exception as e:
            logger.error(f"Failed to get camera {camera_id}: {e}")
            return None

    @staticmethod
    def update_ip_camera(
        db,
        camera_id: int,
        name: str = None,
        manufacturer: str = None,
        ip: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        channel: int = None,
        subtype: int = None,
        rtsp_url: str = None,
        type: str = None,
        is_active: bool = None
    ) -> Optional[Dict]:
        """
        Update camera details.

        Args:
            camera_id: Camera ID to update
            name: New camera name
            manufacturer: New manufacturer
            ip: New IP address
            port: New port
            username: New username
            password: New password
            channel: New channel
            subtype: New subtype
            rtsp_url: New RTSP URL
            type: New camera type
            is_active: New active status

        Returns:
            Updated camera dict or None
        """
        try:
            # Build dynamic UPDATE query with parameterized values
            update_fields = []
            params = {'camera_id': camera_id}

            if name is not None:
                update_fields.append("name = :name")
                params['name'] = name

            if manufacturer is not None:
                update_fields.append("manufacturer = :manufacturer")
                params['manufacturer'] = manufacturer

            if ip is not None:
                if not CameraService._is_valid_ip(ip):
                    logger.error(f"Invalid IP address: {ip}")
                    return None
                update_fields.append("ip = :ip")
                params['ip'] = ip

            if port is not None:
                if not (1 <= port <= 65535):
                    logger.error(f"Invalid port: {port}")
                    return None
                update_fields.append("port = :port")
                params['port'] = port

            if username is not None:
                update_fields.append("username = :username")
                params['username'] = username

            if password is not None:
                update_fields.append("password = :password")
                params['password'] = password

            if channel is not None:
                update_fields.append("channel = :channel")
                params['channel'] = channel

            if subtype is not None:
                update_fields.append("subtype = :subtype")
                params['subtype'] = subtype

            if rtsp_url is not None:
                update_fields.append("rtsp_url = :rtsp_url")
                params['rtsp_url'] = rtsp_url

            if type is not None:
                update_fields.append("type = :type")
                params['type'] = type

            if is_active is not None:
                update_fields.append("is_active = :is_active")
                params['is_active'] = is_active

            if not update_fields:
                return CameraService.get_camera_by_id(db, camera_id)

            # Use text() with safe field names (no user input in field names)
            query = text("""
                UPDATE ip_cameras
                SET {0}
                WHERE id = :camera_id
                RETURNING *
            """.format(', '.join(update_fields)))

            result = db.execute(query, params)
            db.commit()
            row = result.fetchone()

            logger.info(f"Updated camera {camera_id}")
            return CameraService._row_to_ip_camera_dict(row)

        except Exception as e:
            logger.error(f"Failed to update camera {camera_id}: {e}")
            db.rollback()
            return None

    @staticmethod
    def delete_ip_camera(db, camera_id: int) -> bool:
        """
        Delete camera by ID.

        Args:
            camera_id: Camera ID to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            query = text("DELETE FROM ip_cameras WHERE id = :camera_id")
            result = db.execute(query, {'camera_id': camera_id})
            db.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"Deleted camera {camera_id}")
            else:
                logger.warning(f"Camera {camera_id} not found")

            return deleted

        except Exception as e:
            logger.error(f"Failed to delete camera {camera_id}: {e}")
            db.rollback()
            return False

    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """
        Validate IP address format.

        Args:
            ip: IP address string

        Returns:
            True if valid, False otherwise
        """
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False

    @staticmethod
    def _row_to_ip_camera_dict(row) -> Dict:
        """
        Convert database row to camera dictionary.
        Password is masked for security.

        Args:
            row: Database result row

        Returns:
            Camera dictionary
        """
        return {
            'id': row[0],
            'user_id': row[1],
            'name': row[2],
            'manufacturer': row[3],
            'type': row[4],
            'ip': row[5],
            'port': row[6],
            'username': row[7],
            'password': '***' if row[8] else None,  # Mask password
            'channel': row[9],
            'subtype': row[10],
            'rtsp_url': row[11],
            'is_active': row[12],
            'last_connected_at': row[13].isoformat() if row[13] else None,
            'connection_error': row[14],
            'created_at': row[15].isoformat() if row[15] else None
        }