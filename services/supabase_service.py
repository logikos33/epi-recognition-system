"""
Supabase Service - Wrapper for Supabase client (Cloud database)
"""
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from supabase import create_client, Client
from utils.logger import get_logger
from utils.config import get_config


class SupabaseService:
    """
    Wrapper service for Supabase database operations
    """

    def __init__(self, use_service_key: bool = False):
        """
        Initialize Supabase client

        Args:
            use_service_key: If True, use service key for admin operations
        """
        self.logger = get_logger(__name__)
        self.config = get_config()

        url = self.config.supabase_url
        key = self.config.supabase_key if not use_service_key else self.config.supabase_service_key

        if not url or not key:
            raise ValueError(
                "Supabase credentials not found. "
                "Set SUPABASE_URL and SUPABASE_KEY environment variables."
            )

        self.client: Client = create_client(url, key)
        self.logger.info("Supabase client initialized successfully")

    # ==================== CAMERA OPERATIONS ====================

    def get_active_cameras(self) -> List[Dict[str, Any]]:
        """
        Get all active cameras from the database

        Returns:
            List of camera dictionaries
        """
        try:
            response = self.client.table('cameras').select('*').eq('is_active', True).execute()
            return response.data
        except Exception as e:
            self.logger.error(f"Error fetching active cameras: {e}")
            return []

    def get_all_cameras(self) -> List[Dict[str, Any]]:
        """
        Get all cameras (active and inactive)

        Returns:
            List of camera dictionaries
        """
        try:
            response = self.client.table('cameras').select('*').execute()
            return response.data
        except Exception as e:
            self.logger.error(f"Error fetching all cameras: {e}")
            return []

    def get_camera_by_id(self, camera_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a specific camera by ID

        Args:
            camera_id: Camera ID

        Returns:
            Camera dictionary or None
        """
        try:
            response = self.client.table('cameras').select('*').eq('id', camera_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            self.logger.error(f"Error fetching camera {camera_id}: {e}")
            return None

    def create_camera(self, camera_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Create a new camera

        Args:
            camera_data: Dictionary with camera fields

        Returns:
            Created camera dictionary or None
        """
        try:
            response = self.client.table('cameras').insert(camera_data).execute()
            self.logger.info(f"Camera created: {response.data[0]['id']}")
            return response.data[0]
        except Exception as e:
            self.logger.error(f"Error creating camera: {e}")
            return None

    def update_camera(self, camera_id: int, camera_data: Dict[str, Any]) -> bool:
        """
        Update an existing camera

        Args:
            camera_id: Camera ID
            camera_data: Dictionary with fields to update

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.table('cameras').update(camera_data).eq('id', camera_id).execute()
            self.logger.info(f"Camera {camera_id} updated")
            return True
        except Exception as e:
            self.logger.error(f"Error updating camera {camera_id}: {e}")
            return False

    def delete_camera(self, camera_id: int) -> bool:
        """
        Delete a camera

        Args:
            camera_id: Camera ID

        Returns:
            True if successful, False otherwise
        """
        try:
            self.client.table('cameras').delete().eq('id', camera_id).execute()
            self.logger.info(f"Camera {camera_id} deleted")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting camera {camera_id}: {e}")
            return False

    def get_cameras_in_range(self, start_id: int, end_id: int) -> List[Dict[str, Any]]:
        """
        Get cameras within ID range (for worker partitioning)

        Args:
            start_id: Start of ID range
            end_id: End of ID range

        Returns:
            List of camera dictionaries
        """
        try:
            response = self.client.table('cameras').select('*').gte('id', start_id).lte('id', end_id).eq('is_active', True).execute()
            return response.data
        except Exception as e:
            self.logger.error(f"Error fetching cameras in range {start_id}-{end_id}: {e}")
            return []

    # ==================== DETECTION OPERATIONS ====================

    def insert_detection(self, detection_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Insert a new detection record

        Args:
            detection_data: Dictionary with detection fields

        Returns:
            Created detection dictionary or None
        """
        try:
            response = self.client.table('detections').insert(detection_data).execute()
            return response.data[0]
        except Exception as e:
            self.logger.error(f"Error inserting detection: {e}")
            return None

    def get_recent_detections(
        self,
        limit: int = 50,
        camera_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get recent detections

        Args:
            limit: Maximum number of detections to return
            camera_id: Filter by camera ID (optional)

        Returns:
            List of detection dictionaries
        """
        try:
            query = self.client.table('detections').select('*').order('timestamp', desc=True).limit(limit)

            if camera_id is not None:
                query = query.eq('camera_id', camera_id)

            response = query.execute()
            return response.data
        except Exception as e:
            self.logger.error(f"Error fetching recent detections: {e}")
            return []

    def get_detections_in_range(
        self,
        start_time: datetime,
        end_time: datetime,
        camera_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get detections within a time range

        Args:
            start_time: Start of time range
            end_time: End of time range
            camera_id: Filter by camera ID (optional)

        Returns:
            List of detection dictionaries
        """
        try:
            query = self.client.table('detections').select('*') \
                .gte('timestamp', start_time.isoformat()) \
                .lte('timestamp', end_time.isoformat()) \
                .order('timestamp', desc=True)

            if camera_id is not None:
                query = query.eq('camera_id', camera_id)

            response = query.execute()
            return response.data
        except Exception as e:
            self.logger.error(f"Error fetching detections in range: {e}")
            return []

    def get_compliance_stats(
        self,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Get compliance statistics for the last N hours

        Args:
            hours: Number of hours to look back

        Returns:
            Dictionary with compliance statistics
        """
        try:
            start_time = datetime.now() - timedelta(hours=hours)

            # Get all detections in range
            detections = self.get_detections_in_range(start_time, datetime.now())

            if not detections:
                return {
                    "total": 0,
                    "compliant": 0,
                    "non_compliant": 0,
                    "compliance_rate": 0.0,
                    "person_count": 0
                }

            total = len(detections)
            compliant = sum(1 for d in detections if d.get('is_compliant', False))
            non_compliant = total - compliant
            person_count = sum(d.get('person_count', 0) for d in detections)

            return {
                "total": total,
                "compliant": compliant,
                "non_compliant": non_compliant,
                "compliance_rate": (compliant / total * 100) if total > 0 else 0.0,
                "person_count": person_count
            }
        except Exception as e:
            self.logger.error(f"Error calculating compliance stats: {e}")
            return {
                "total": 0,
                "compliant": 0,
                "non_compliant": 0,
                "compliance_rate": 0.0,
                "person_count": 0
            }

    # ==================== WORKER STATUS OPERATIONS ====================

    def update_worker_heartbeat(
        self,
        worker_id: str,
        active_cameras: List[int],
        status: str = "active"
    ) -> bool:
        """
        Update worker heartbeat and status

        Args:
            worker_id: Unique worker identifier
            active_cameras: List of camera IDs being processed
            status: Worker status (active, idle, error)

        Returns:
            True if successful, False otherwise
        """
        try:
            data = {
                "worker_id": worker_id,
                "status": status,
                "active_cameras": active_cameras,
                "last_heartbeat": datetime.now().isoformat()
            }

            # Upsert using RPC or manual check
            existing = self.client.table('worker_status').select('*').eq('worker_id', worker_id).execute()

            if existing.data:
                self.client.table('worker_status').update(data).eq('worker_id', worker_id).execute()
            else:
                self.client.table('worker_status').insert(data).execute()

            return True
        except Exception as e:
            self.logger.error(f"Error updating worker heartbeat: {e}")
            return False

    def get_worker_status(self, worker_id: str) -> Optional[Dict[str, Any]]:
        """
        Get worker status

        Args:
            worker_id: Worker identifier

        Returns:
            Worker status dictionary or None
        """
        try:
            response = self.client.table('worker_status').select('*').eq('worker_id', worker_id).execute()
            if response.data:
                return response.data[0]
            return None
        except Exception as e:
            self.logger.error(f"Error fetching worker status: {e}")
            return None

    def get_all_workers(self) -> List[Dict[str, Any]]:
        """
        Get all worker statuses

        Returns:
            List of worker status dictionaries
        """
        try:
            response = self.client.table('worker_status').select('*').execute()
            return response.data
        except Exception as e:
            self.logger.error(f"Error fetching all workers: {e}")
            return []

    def cleanup_stale_workers(self, timeout_minutes: int = 5) -> int:
        """
        Mark workers as stale if they haven't sent heartbeat recently

        Args:
            timeout_minutes: Minutes since last heartbeat

        Returns:
            Number of workers marked as stale
        """
        try:
            timeout_time = datetime.now() - timedelta(minutes=timeout_minutes)

            stale_workers = self.client.table('worker_status') \
                .select('*') \
                .lt('last_heartbeat', timeout_time.isoformat()) \
                .eq('status', 'active') \
                .execute()

            count = 0
            for worker in stale_workers.data:
                self.client.table('worker_status') \
                    .update({"status": "stale"}) \
                    .eq('worker_id', worker['worker_id']) \
                    .execute()
                count += 1
                self.logger.warning(f"Worker {worker['worker_id']} marked as stale")

            return count
        except Exception as e:
            self.logger.error(f"Error cleaning up stale workers: {e}")
            return 0


# Global instance
_supabase_instance: Optional[SupabaseService] = None


def get_supabase_service(use_service_key: bool = False) -> SupabaseService:
    """
    Get or create Supabase service instance

    Args:
        use_service_key: If True, use service key for admin operations

    Returns:
        SupabaseService instance
    """
    global _supabase_instance

    if _supabase_instance is None:
        _supabase_instance = SupabaseService(use_service_key=use_service_key)

    return _supabase_instance
