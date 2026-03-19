"""
Database Service - CRUD Operations and Session Management
"""
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from contextlib import contextmanager
from sqlalchemy import create_engine, func, and_, or_
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from models.database import Base, Camera, Detection, EPIType, Alert
from models.schemas import (
    CameraCreate, CameraUpdate, CameraResponse,
    EPITypeCreate, EPITypeUpdate, EPITypeResponse,
    DetectionCreate, DetectionUpdate, DetectionResponse,
    AlertCreate, AlertResponse,
    ComplianceStats, CameraStats, TimeSeriesData
)
from utils.logger import get_logger
from utils.config import get_config


class DatabaseService:
    """
    Service for database operations
    """

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database service

        Args:
            database_url: Database connection URL
        """
        self.logger = get_logger(__name__)
        self.config = get_config()

        self.database_url = database_url or self.config.database_url

        # Create engine
        self.engine = create_engine(
            self.database_url,
            poolclass=StaticPool,
            connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {},
            echo=self.config.debug
        )

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

        # Initialize database
        self._init_database()

    def _init_database(self):
        """
        Initialize database tables
        """
        try:
            Base.metadata.create_all(bind=self.engine)
            self.logger.info("Database initialized successfully")

            # Create default EPI types if they don't exist
            self._create_default_epi_types()

        except Exception as e:
            self.logger.error(f"Error initializing database: {e}")
            raise

    def _create_default_epi_types(self):
        """
        Create default EPI types in database
        """
        with self.get_session() as session:
            existing_types = session.query(EPIType).count()

            if existing_types == 0:
                default_types = [
                    EPIType(name="helmet", description="Capacete de segurança", required=True),
                    EPIType(name="gloves", description="Luvas de proteção", required=True),
                    EPIType(name="glasses", description="Óculos de proteção", required=True),
                    EPIType(name="vest", description="Colete refletivo", required=True),
                    EPIType(name="boots", description="Botas de segurança", required=False),
                ]

                for epi_type in default_types:
                    session.add(epi_type)

                session.commit()
                self.logger.info("Created default EPI types")

    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions

        Yields:
            Session: SQLAlchemy session
        """
        session = self.SessionLocal()
        try:
            yield session
        except Exception as e:
            session.rollback()
            self.logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()

    # Camera Operations
    def create_camera(self, camera_data: CameraCreate) -> CameraResponse:
        """
        Create a new camera

        Args:
            camera_data: Camera creation data

        Returns:
            Created camera
        """
        with self.get_session() as session:
            db_camera = Camera(**camera_data.dict())
            session.add(db_camera)
            session.commit()
            session.refresh(db_camera)

            self.logger.info(f"Created camera: {db_camera.name}")
            return CameraResponse.from_orm(db_camera)

    def get_camera(self, camera_id: int) -> Optional[CameraResponse]:
        """
        Get camera by ID

        Args:
            camera_id: Camera ID

        Returns:
            Camera or None
        """
        with self.get_session() as session:
            db_camera = session.query(Camera).filter(Camera.id == camera_id).first()
            return CameraResponse.from_orm(db_camera) if db_camera else None

    def get_all_cameras(self, active_only: bool = False) -> List[CameraResponse]:
        """
        Get all cameras

        Args:
            active_only: Whether to return only active cameras

        Returns:
            List of cameras
        """
        with self.get_session() as session:
            query = session.query(Camera)

            if active_only:
                query = query.filter(Camera.is_active == True)

            db_cameras = query.all()
            return [CameraResponse.from_orm(camera) for camera in db_cameras]

    def update_camera(self, camera_id: int, camera_data: CameraUpdate) -> Optional[CameraResponse]:
        """
        Update camera

        Args:
            camera_id: Camera ID
            camera_data: Update data

        Returns:
            Updated camera or None
        """
        with self.get_session() as session:
            db_camera = session.query(Camera).filter(Camera.id == camera_id).first()

            if not db_camera:
                return None

            for field, value in camera_data.dict(exclude_unset=True).items():
                setattr(db_camera, field, value)

            session.commit()
            session.refresh(db_camera)

            self.logger.info(f"Updated camera: {db_camera.name}")
            return CameraResponse.from_orm(db_camera)

    def delete_camera(self, camera_id: int) -> bool:
        """
        Delete camera

        Args:
            camera_id: Camera ID

        Returns:
            True if deleted, False if not found
        """
        with self.get_session() as session:
            db_camera = session.query(Camera).filter(Camera.id == camera_id).first()

            if not db_camera:
                return False

            session.delete(db_camera)
            session.commit()

            self.logger.info(f"Deleted camera: {camera_id}")
            return True

    # Detection Operations
    def create_detection(self, detection_data: DetectionCreate) -> DetectionResponse:
        """
        Create a new detection

        Args:
            detection_data: Detection creation data

        Returns:
            Created detection
        """
        with self.get_session() as session:
            db_detection = Detection(**detection_data.dict())
            session.add(db_detection)
            session.commit()
            session.refresh(db_detection)

            return DetectionResponse.from_orm(db_detection)

    def get_detection(self, detection_id: int) -> Optional[DetectionResponse]:
        """
        Get detection by ID

        Args:
            detection_id: Detection ID

        Returns:
            Detection or None
        """
        with self.get_session() as session:
            db_detection = session.query(Detection).filter(Detection.id == detection_id).first()
            return DetectionResponse.from_orm(db_detection) if db_detection else None

    def get_detections_by_camera(
        self,
        camera_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[DetectionResponse]:
        """
        Get detections for a camera

        Args:
            camera_id: Camera ID
            start_date: Start date filter
            end_date: End date filter
            limit: Maximum number of results

        Returns:
            List of detections
        """
        with self.get_session() as session:
            query = session.query(Detection).filter(Detection.camera_id == camera_id)

            if start_date:
                query = query.filter(Detection.timestamp >= start_date)

            if end_date:
                query = query.filter(Detection.timestamp <= end_date)

            query = query.order_by(Detection.timestamp.desc()).limit(limit)

            db_detections = query.all()
            return [DetectionResponse.from_orm(d) for d in db_detections]

    def get_recent_detections(self, limit: int = 50) -> List[DetectionResponse]:
        """
        Get recent detections across all cameras

        Args:
            limit: Maximum number of results

        Returns:
            List of recent detections
        """
        with self.get_session() as session:
            db_detections = session.query(Detection)\
                .order_by(Detection.timestamp.desc())\
                .limit(limit)\
                .all()

            return [DetectionResponse.from_orm(d) for d in db_detections]

    def get_non_compliant_detections(self, limit: int = 50) -> List[DetectionResponse]:
        """
        Get non-compliant detections

        Args:
            limit: Maximum number of results

        Returns:
            List of non-compliant detections
        """
        with self.get_session() as session:
            db_detections = session.query(Detection)\
                .filter(Detection.is_compliant == False)\
                .order_by(Detection.timestamp.desc())\
                .limit(limit)\
                .all()

            return [DetectionResponse.from_orm(d) for d in db_detections]

    # Alert Operations
    def create_alert(self, alert_data: AlertCreate) -> AlertResponse:
        """
        Create a new alert

        Args:
            alert_data: Alert creation data

        Returns:
            Created alert
        """
        with self.get_session() as session:
            db_alert = Alert(**alert_data.dict())
            session.add(db_alert)
            session.commit()
            session.refresh(db_alert)

            self.logger.warning(f"Created alert: {db_alert.message}")
            return AlertResponse.from_orm(db_alert)

    def get_alerts(
        self,
        unresolved_only: bool = False,
        limit: int = 50
    ) -> List[AlertResponse]:
        """
        Get alerts

        Args:
            unresolved_only: Whether to return only unresolved alerts
            limit: Maximum number of results

        Returns:
            List of alerts
        """
        with self.get_session() as session:
            query = session.query(Alert)

            if unresolved_only:
                query = query.filter(Alert.is_resolved == False)

            query = query.order_by(Alert.created_at.desc()).limit(limit)

            db_alerts = query.all()
            return [AlertResponse.from_orm(a) for a in db_alerts]

    def resolve_alert(self, alert_id: int) -> Optional[AlertResponse]:
        """
        Resolve an alert

        Args:
            alert_id: Alert ID

        Returns:
            Updated alert or None
        """
        with self.get_session() as session:
            db_alert = session.query(Alert).filter(Alert.id == alert_id).first()

            if not db_alert:
                return None

            db_alert.is_resolved = True
            db_alert.resolved_at = datetime.utcnow()

            session.commit()
            session.refresh(db_alert)

            return AlertResponse.from_orm(db_alert)

    # Statistics and Analytics
    def get_compliance_stats(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> ComplianceStats:
        """
        Get compliance statistics

        Args:
            start_date: Start date
            end_date: End date

        Returns:
            Compliance statistics
        """
        with self.get_session() as session:
            query = session.query(Detection)

            if start_date:
                query = query.filter(Detection.timestamp >= start_date)

            if end_date:
                query = query.filter(Detection.timestamp <= end_date)

            detections = query.all()

            total = len(detections)
            compliant = sum(1 for d in detections if d.is_compliant)
            non_compliant = total - compliant

            compliance_rate = (compliant / total * 100) if total > 0 else 0

            # Calculate EPI detection rates
            epi_counts = {}
            for detection in detections:
                for epi_type, detected in detection.epis_detected.items():
                    if epi_type not in epi_counts:
                        epi_counts[epi_type] = {"detected": 0, "total": 0}
                    epi_counts[epi_type]["total"] += 1
                    if detected:
                        epi_counts[epi_type]["detected"] += 1

            epi_detection_rates = {}
            for epi_type, counts in epi_counts.items():
                rate = (counts["detected"] / counts["total"] * 100) if counts["total"] > 0 else 0
                epi_detection_rates[epi_type] = round(rate, 2)

            return ComplianceStats(
                total_detections=total,
                compliant_detections=compliant,
                non_compliant_detections=non_compliant,
                compliance_rate=round(compliance_rate, 2),
                epi_detection_rates=epi_detection_rates
            )

    def get_camera_stats(
        self,
        camera_id: Optional[int] = None,
        days: int = 7
    ) -> List[CameraStats]:
        """
        Get statistics for cameras

        Args:
            camera_id: Specific camera ID (None for all)
            days: Number of days to analyze

        Returns:
            List of camera statistics
        """
        start_date = datetime.utcnow() - timedelta(days=days)

        with self.get_session() as session:
            if camera_id:
                cameras = session.query(Camera).filter(Camera.id == camera_id).all()
            else:
                cameras = session.query(Camera).filter(Camera.is_active == True).all()

            stats_list = []

            for camera in cameras:
                detections = session.query(Detection)\
                    .filter(
                        and_(
                            Detection.camera_id == camera.id,
                            Detection.timestamp >= start_date
                        )
                    )\
                    .all()

                total = len(detections)
                compliant = sum(1 for d in detections if d.is_compliant)
                compliance_rate = (compliant / total * 100) if total > 0 else 0

                last_detection = detections[0].timestamp if detections else None

                stats = CameraStats(
                    camera_id=camera.id,
                    camera_name=camera.name,
                    total_detections=total,
                    compliance_rate=round(compliance_rate, 2),
                    last_detection=last_detection
                )

                stats_list.append(stats)

            return stats_list

    def get_compliance_over_time(
        self,
        days: int = 7,
        interval_hours: int = 24
    ) -> List[TimeSeriesData]:
        """
        Get compliance rate over time

        Args:
            days: Number of days to analyze
            interval_hours: Interval between data points

        Returns:
            List of time series data points
        """
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        with self.get_session() as session:
            time_series = []

            current_date = start_date
            while current_date <= end_date:
                next_date = current_date + timedelta(hours=interval_hours)

                detections = session.query(Detection)\
                    .filter(
                        and_(
                            Detection.timestamp >= current_date,
                            Detection.timestamp < next_date
                        )
                    )\
                    .all()

                total = len(detections)
                compliant = sum(1 for d in detections if d.is_compliant)
                compliance_rate = (compliant / total * 100) if total > 0 else 0

                time_series.append(
                    TimeSeriesData(
                        timestamp=current_date,
                        value=round(compliance_rate, 2),
                        label=f"{compliant}/{total}"
                    )
                )

                current_date = next_date

            return time_series

    # EPI Type Operations
    def get_all_epi_types(self) -> List[EPITypeResponse]:
        """
        Get all EPI types

        Returns:
            List of EPI types
        """
        with self.get_session() as session:
            epi_types = session.query(EPIType).all()
            return [EPITypeResponse.from_orm(e) for e in epi_types]

    def update_epi_type(
        self,
        epi_type_id: int,
        epi_data: EPITypeUpdate
    ) -> Optional[EPITypeResponse]:
        """
        Update EPI type

        Args:
            epi_type_id: EPI type ID
            epi_data: Update data

        Returns:
            Updated EPI type or None
        """
        with self.get_session() as session:
            db_epi = session.query(EPIType).filter(EPIType.id == epi_type_id).first()

            if not db_epi:
                return None

            for field, value in epi_data.dict(exclude_unset=True).items():
                setattr(db_epi, field, value)

            session.commit()
            session.refresh(db_epi)

            return EPITypeResponse.from_orm(db_epi)

    def cleanup_old_detections(self, days: int = 30) -> int:
        """
        Cleanup old detections from database

        Args:
            days: Number of days to keep

        Returns:
            Number of deleted records
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        with self.get_session() as session:
            deleted = session.query(Detection)\
                .filter(Detection.timestamp < cutoff_date)\
                .delete()

            session.commit()

            self.logger.info(f"Cleaned up {deleted} old detections")
            return deleted


def get_database_service() -> DatabaseService:
    """
    Get or create database service instance

    Returns:
        DatabaseService: Database service instance
    """
    return DatabaseService()
