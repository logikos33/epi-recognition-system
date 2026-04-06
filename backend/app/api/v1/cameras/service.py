"""Camera service."""
import logging
import uuid

from backend.app.core.validators import RTSPUrlValidator
from backend.app.infrastructure.database.connection import db_pool

logger = logging.getLogger(__name__)

RTSP_TEMPLATES = {
    "intelbras": "rtsp://{username}:{password}@{ip}:{port}/cam/realmonitor?channel=1&subtype=0",
    "hikvision": "rtsp://{username}:{password}@{ip}:{port}/Streaming/Channels/101",
    "generic": "rtsp://{username}:{password}@{ip}:{port}/stream",
}


def build_rtsp_url(manufacturer: str, ip: str, port: int, username: str, password: str) -> str:
    template = RTSP_TEMPLATES.get(manufacturer, RTSP_TEMPLATES["generic"])
    url = template.format(username=username, password=password, ip=ip, port=port)
    RTSPUrlValidator.validate(url)
    return url


class CameraService:

    @staticmethod
    def list_cameras(user_id: str) -> list:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "SELECT id, user_id, name, manufacturer, ip, port, username, is_active, created_at FROM ip_cameras WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            return [dict(r) for r in cur.fetchall()]

    @staticmethod
    def create_camera(user_id: str, data: dict) -> dict:
        name = data.get("name", "").strip()
        manufacturer = data.get("manufacturer", "generic").lower()
        ip = data.get("ip", "").strip()
        port = int(data.get("port", 554))
        username = data.get("username", "")
        password = data.get("password", "")

        if not name or not ip:
            from backend.app.core.exceptions import ValidationError
            raise ValidationError("name and ip are required")

        rtsp_url = build_rtsp_url(manufacturer, ip, port, username, password)
        camera_id = str(uuid.uuid4())

        with db_pool.get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO ip_cameras (id, user_id, name, manufacturer, ip, port, username, rtsp_url, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                RETURNING id, user_id, name, manufacturer, ip, port, username, is_active, created_at
                """,
                (camera_id, user_id, name, manufacturer, ip, port, username, rtsp_url),
            )
            return dict(cur.fetchone())

    @staticmethod
    def get_camera(user_id: str, camera_id: str) -> dict | None:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "SELECT id, user_id, name, manufacturer, ip, port, username, rtsp_url, is_active, created_at FROM ip_cameras WHERE id = %s AND user_id = %s",
                (camera_id, user_id),
            )
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def update_camera(user_id: str, camera_id: str, data: dict) -> dict | None:
        name = data.get("name")
        ip = data.get("ip")
        port = data.get("port")

        with db_pool.get_cursor() as cur:
            updates = []
            values = []
            if name:
                updates.append("name = %s")
                values.append(name.strip())
            if ip:
                updates.append("ip = %s")
                values.append(ip.strip())
            if port:
                updates.append("port = %s")
                values.append(int(port))

            if not updates:
                return CameraService.get_camera(user_id, camera_id)

            values.extend([camera_id, user_id])
            cur.execute(
                f"UPDATE ip_cameras SET {', '.join(updates)} WHERE id = %s AND user_id = %s RETURNING id, name, ip, port, is_active",
                values,
            )
            row = cur.fetchone()
            return dict(row) if row else None

    @staticmethod
    def delete_camera(user_id: str, camera_id: str) -> None:
        with db_pool.get_cursor() as cur:
            cur.execute(
                "DELETE FROM ip_cameras WHERE id = %s AND user_id = %s",
                (camera_id, user_id),
            )
