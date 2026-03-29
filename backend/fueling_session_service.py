"""
Fueling Session Service for Fueling Monitoring System

Handles CRUD operations for fueling sessions and counted products.
"""
from sqlalchemy import text
from typing import List, Dict, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Whitelist of allowed fields for update_session() to prevent SQL injection
ALLOWED_UPDATE_FIELDS = {
    'license_plate',
    'truck_exit_time',
    'duration_seconds',
    'final_weight',
    'status'
}


class FuelingSessionService:
    """Service for managing fueling sessions"""

    @staticmethod
    def create_session(
        db,
        bay_id: int,
        camera_id: int,
        license_plate: str,
        truck_entry_time: datetime = None
    ) -> Optional[Dict]:
        """
        Create a new fueling session.

        Returns:
            Session dict or None if failed
        """
        try:
            if truck_entry_time is None:
                truck_entry_time = datetime.now()

            query = text("""
                INSERT INTO fueling_sessions (
                    bay_id, camera_id, license_plate, truck_entry_time, status
                )
                VALUES (:bay_id, :camera_id, :license_plate, :truck_entry_time, 'active')
                RETURNING *
            """)
            result = db.execute(query, {
                'bay_id': bay_id,
                'camera_id': camera_id,
                'license_plate': license_plate,
                'truck_entry_time': truck_entry_time
            })
            db.commit()
            row = result.fetchone()

            logger.info(f"✅ Created fueling session: {license_plate}")
            return {
                'id': str(row[0]),
                'bay_id': row[1],
                'camera_id': row[2],
                'license_plate': row[3],
                'truck_entry_time': row[4].isoformat() if row[4] else None,
                'truck_exit_time': row[5].isoformat() if row[5] else None,
                'duration_seconds': row[6],
                # Note: products_counted is JSONB field - returns dict/list, not integer
                'products_counted': row[7],
                'final_weight': row[8],
                'status': row[9],
                'created_at': row[10].isoformat() if row[10] else None
            }

        except Exception as e:
            logger.error(f"❌ Failed to create fueling session: {e}")
            db.rollback()
            return None

    @staticmethod
    def get_session_by_id(db, session_id: str) -> Optional[Dict]:
        """
        Get fueling session by ID.

        Returns:
            Session dict or None
        """
        try:
            query = text("""
                SELECT * FROM fueling_sessions
                WHERE id = :session_id
            """)
            result = db.execute(query, {'session_id': session_id})
            row = result.fetchone()

            if not row:
                return None

            return {
                'id': str(row[0]),
                'bay_id': row[1],
                'camera_id': row[2],
                'license_plate': row[3],
                'truck_entry_time': row[4].isoformat() if row[4] else None,
                'truck_exit_time': row[5].isoformat() if row[5] else None,
                'duration_seconds': row[6],
                # Note: products_counted is JSONB field - returns dict/list, not integer
                'products_counted': row[7],
                'final_weight': row[8],
                'status': row[9],
                'created_at': row[10].isoformat() if row[10] else None
            }

        except Exception as e:
            logger.error(f"❌ Failed to get session {session_id}: {e}")
            return None

    @staticmethod
    def list_sessions(
        db,
        bay_id: int = None,
        status: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """
        List fueling sessions with optional filters.

        Returns:
            List of session dicts
        """
        try:
            # Build dynamic query with filters
            conditions = []
            params = {'limit': limit}

            if bay_id is not None:
                conditions.append("bay_id = :bay_id")
                params['bay_id'] = bay_id

            if status is not None:
                conditions.append("status = :status")
                params['status'] = status

            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)

            query = text(f"""
                SELECT * FROM fueling_sessions
                {where_clause}
                ORDER BY truck_entry_time DESC
                LIMIT :limit
            """)
            result = db.execute(query, params)
            rows = result.fetchall()

            sessions = []
            for row in rows:
                sessions.append({
                    'id': str(row[0]),
                    'bay_id': row[1],
                    'camera_id': row[2],
                    'license_plate': row[3],
                    'truck_entry_time': row[4].isoformat() if row[4] else None,
                    'truck_exit_time': row[5].isoformat() if row[5] else None,
                    'duration_seconds': row[6],
                    # Note: products_counted is JSONB field - returns dict/list, not integer
                    'products_counted': row[7],
                    'final_weight': row[8],
                    'status': row[9],
                    'created_at': row[10].isoformat() if row[10] else None
                })

            return sessions

        except Exception as e:
            logger.error(f"❌ Failed to list sessions: {e}")
            return []

    @staticmethod
    def update_session(
        db,
        session_id: str,
        license_plate: str = None,
        truck_exit_time: datetime = None,
        duration_seconds: int = None,
        final_weight: float = None,
        status: str = None
    ) -> Optional[Dict]:
        """
        Update fueling session fields.

        Returns:
            Updated session dict or None
        """
        try:
            # Build dynamic UPDATE query with field validation to prevent SQL injection
            update_fields = []
            params = {'session_id': session_id}

            # Map parameter names to actual column names for validation
            field_mapping = {
                'license_plate': 'license_plate',
                'truck_exit_time': 'truck_exit_time',
                'duration_seconds': 'duration_seconds',
                'final_weight': 'final_weight',
                'status': 'status'
            }

            if license_plate is not None:
                update_fields.append("license_plate = :license_plate")
                params['license_plate'] = license_plate

            if truck_exit_time is not None:
                update_fields.append("truck_exit_time = :truck_exit_time")
                params['truck_exit_time'] = truck_exit_time

            if duration_seconds is not None:
                update_fields.append("duration_seconds = :duration_seconds")
                params['duration_seconds'] = duration_seconds

            if final_weight is not None:
                update_fields.append("final_weight = :final_weight")
                params['final_weight'] = final_weight

            if status is not None:
                update_fields.append("status = :status")
                params['status'] = status

            # Validate all fields are in allowed whitelist (SQL injection prevention)
            for field in update_fields:
                field_name = field.split(' =')[0].strip()
                if field_name not in ALLOWED_UPDATE_FIELDS:
                    logger.error(f"❌ Invalid field '{field_name}' not in ALLOWED_UPDATE_FIELDS")
                    raise ValueError(f"Invalid field '{field_name}' for update")

            if not update_fields:
                return FuelingSessionService.get_session_by_id(db, session_id)

            query = text(f"""
                UPDATE fueling_sessions
                SET {', '.join(update_fields)}
                WHERE id = :session_id
                RETURNING *
            """)
            result = db.execute(query, params)
            db.commit()
            row = result.fetchone()

            if not row:
                logger.warning(f"⚠️ Session {session_id} not found for update")
                return None

            logger.info(f"✅ Updated fueling session {session_id}")
            return {
                'id': str(row[0]),
                'bay_id': row[1],
                'camera_id': row[2],
                'license_plate': row[3],
                'truck_entry_time': row[4].isoformat() if row[4] else None,
                'truck_exit_time': row[5].isoformat() if row[5] else None,
                'duration_seconds': row[6],
                # Note: products_counted is JSONB field - returns dict/list, not integer
                'products_counted': row[7],
                'final_weight': row[8],
                'status': row[9],
                'created_at': row[10].isoformat() if row[10] else None
            }

        except Exception as e:
            logger.error(f"❌ Failed to update session {session_id}: {e}")
            db.rollback()
            return None

    @staticmethod
    def complete_session(
        db,
        session_id: str,
        truck_exit_time: datetime = None
    ) -> Optional[Dict]:
        """
        Mark fueling session as completed.

        Returns:
            Updated session dict or None
        """
        try:
            if truck_exit_time is None:
                truck_exit_time = datetime.now()

            # Atomic UPDATE with SQL-based duration calculation to prevent race condition
            # This eliminates the read-then-write pattern that could cause inconsistencies
            query = text("""
                UPDATE fueling_sessions
                SET status = 'completed',
                    truck_exit_time = :truck_exit_time,
                    duration_seconds = EXTRACT(EPOCH FROM (:truck_exit_time - truck_entry_time))::INTEGER
                WHERE id = :session_id
                RETURNING *
            """)
            result = db.execute(query, {
                'session_id': session_id,
                'truck_exit_time': truck_exit_time
            })
            db.commit()
            row = result.fetchone()

            if not row:
                logger.warning(f"⚠️ Session {session_id} not found for completion")
                return None

            logger.info(f"✅ Completed fueling session {session_id}")
            return {
                'id': str(row[0]),
                'bay_id': row[1],
                'camera_id': row[2],
                'license_plate': row[3],
                'truck_entry_time': row[4].isoformat() if row[4] else None,
                'truck_exit_time': row[5].isoformat() if row[5] else None,
                'duration_seconds': row[6],
                # Note: products_counted is JSONB field - returns dict/list, not integer
                'products_counted': row[7],
                'final_weight': row[8],
                'status': row[9],
                'created_at': row[10].isoformat() if row[10] else None
            }

        except Exception as e:
            logger.error(f"❌ Failed to complete session {session_id}: {e}")
            db.rollback()
            return None

    @staticmethod
    def add_counted_product(
        db,
        session_id: str,
        product_type: str,
        quantity: int,
        confidence: float = None,
        confirmed_by_user: bool = False
    ) -> Optional[Dict]:
        """
        Add a counted product to a session.

        Returns:
            Product dict or None if failed
        """
        try:
            query = text("""
                INSERT INTO counted_products (
                    session_id, product_type, quantity, confidence, confirmed_by_user
                )
                VALUES (:session_id, :product_type, :quantity, :confidence, :confirmed_by_user)
                RETURNING *
            """)
            result = db.execute(query, {
                'session_id': session_id,
                'product_type': product_type,
                'quantity': quantity,
                'confidence': confidence,
                'confirmed_by_user': confirmed_by_user
            })
            db.commit()
            row = result.fetchone()

            logger.info(f"✅ Added counted product: {product_type} x{quantity}")
            return {
                'id': str(row[0]),
                'session_id': str(row[1]),
                'product_type': row[2],
                'quantity': row[3],
                'confidence': row[4],
                'confirmed_by_user': row[5],
                'is_ai_suggestion': row[6],
                'corrected_to_type': row[7],
                'timestamp': row[8].isoformat() if row[8] else None
            }

        except Exception as e:
            logger.error(f"❌ Failed to add counted product: {e}")
            db.rollback()
            return None

    @staticmethod
    def get_session_products(db, session_id: str) -> List[Dict]:
        """
        Get all counted products for a session.

        Returns:
            List of product dicts
        """
        try:
            query = text("""
                SELECT * FROM counted_products
                WHERE session_id = :session_id
                ORDER BY timestamp ASC
            """)
            result = db.execute(query, {'session_id': session_id})
            rows = result.fetchall()

            products = []
            for row in rows:
                products.append({
                    'id': str(row[0]),
                    'session_id': str(row[1]),
                    'product_type': row[2],
                    'quantity': row[3],
                    'confidence': row[4],
                    'confirmed_by_user': row[5],
                    'is_ai_suggestion': row[6],
                    'corrected_to_type': row[7],
                    'timestamp': row[8].isoformat() if row[8] else None
                })

            return products

        except Exception as e:
            logger.error(f"❌ Failed to get products for session {session_id}: {e}")
            return []
