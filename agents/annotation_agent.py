"""
Annotation Agent - Metadata Enrichment and Persistence
"""
import cv2
import numpy as np
from typing import Optional, Dict, Any, List
from pathlib import Path
from datetime import datetime
import json

from models.schemas import DetectionResult, BoundingBox, DetectionCreate, AlertCreate
from models.database import Detection
from services.database_service import DatabaseService, get_database_service
from utils.logger import get_logger
from utils.config import get_config


class AnnotationAgent:
    """
    Agent responsible for annotating detections with metadata and persisting them
    """

    def __init__(self, database_service: Optional[DatabaseService] = None):
        """
        Initialize annotation agent

        Args:
            database_service: Database service instance
        """
        self.logger = get_logger(__name__)
        self.config = get_config()

        # Initialize database service
        self.db_service = database_service or get_database_service()

        self.logger.info("Annotation Agent initialized")

    def annotate_detection(
        self,
        result: DetectionResult,
        camera_id: int,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DetectionCreate:
        """
        Annotate detection result with metadata

        Args:
            result: Detection result from recognition agent
            camera_id: Camera ID
            metadata: Additional metadata

        Returns:
            DetectionCreate object with all annotations
        """
        # Add timestamp
        timestamp = result.timestamp or datetime.now()

        # Prepare bbox data for storage
        bbox_data = self._prepare_bbox_data(result.detections)

        # Combine metadata
        enriched_metadata = metadata or {}
        enriched_metadata.update({
            "person_count": result.person_count,
            "detection_count": len(result.detections),
            "camera_id": camera_id
        })

        # Create detection object
        detection_create = DetectionCreate(
            camera_id=camera_id,
            epis_detected=result.epis_detected,
            confidence=result.confidence,
            is_compliant=result.is_compliant,
            person_count=result.person_count,
            image_path=result.image_path,
            bbox_data=bbox_data
        )

        self.logger.debug(
            f"Annotated detection from camera {camera_id}: "
            f"compliant={result.is_compliant}, epis={result.epis_detected}"
        )

        return detection_create

    def save_detection(self, detection_create: DetectionCreate) -> Optional[Detection]:
        """
        Save detection to database

        Args:
            detection_create: Detection create object

        Returns:
            Created detection or None
        """
        try:
            detection_response = self.db_service.create_detection(detection_create)
            self.logger.info(f"Saved detection {detection_response.id} to database")
            return detection_response

        except Exception as e:
            self.logger.error(f"Error saving detection to database: {e}")
            return None

    def process_and_save(
        self,
        result: DetectionResult,
        camera_id: int,
        metadata: Optional[Dict[str, Any]] = None,
        save_frame: bool = True
    ) -> Optional[int]:
        """
        Process detection result and save to database

        Args:
            result: Detection result
            camera_id: Camera ID
            metadata: Additional metadata
            save_frame: Whether to save the frame image

        Returns:
            Detection ID or None if failed
        """
        try:
            # Annotate detection
            detection_create = self.annotate_detection(result, camera_id, metadata)

            # Save frame image if requested
            if save_frame and result.image_path:
                self._save_detection_frame(result, camera_id)

            # Save to database
            detection_response = self.save_detection(detection_create)

            # Create alert if non-compliant
            if detection_response and not result.is_compliant:
                self._create_non_compliance_alert(detection_response.id, result)

            return detection_response.id if detection_response else None

        except Exception as e:
            self.logger.error(f"Error processing and saving detection: {e}")
            return None

    def _prepare_bbox_data(self, detections: List[BoundingBox]) -> Dict[str, Any]:
        """
        Prepare bounding box data for storage

        Args:
            detections: List of bounding boxes

        Returns:
            Dictionary with bbox data
        """
        bbox_list = []

        for bbox in detections:
            bbox_data = {
                "x1": bbox.x1,
                "y1": bbox.y1,
                "x2": bbox.x2,
                "y2": bbox.y2,
                "confidence": bbox.confidence,
                "class_name": bbox.class_name
            }
            bbox_list.append(bbox_data)

        return {
            "count": len(bbox_list),
            "bboxes": bbox_list
        }

    def _save_detection_frame(
        self,
        result: DetectionResult,
        camera_id: int
    ):
        """
        Save detection frame with annotations

        Args:
            result: Detection result
            camera_id: Camera ID
        """
        try:
            # This would be called with the actual frame image
            # For now, we'll just log the path
            frame_path = self.config.images_dir / result.image_path

            self.logger.debug(f"Frame saved to: {frame_path}")

        except Exception as e:
            self.logger.error(f"Error saving detection frame: {e}")

    def _create_non_compliance_alert(
        self,
        detection_id: int,
        result: DetectionResult
    ):
        """
        Create alert for non-compliant detection

        Args:
            detection_id: Detection ID
            result: Detection result
        """
        try:
            # Determine severity based on missing EPIs
            severity = self._calculate_alert_severity(result)

            # Generate alert message
            message = self._generate_alert_message(result)

            # Create alert
            alert_create = AlertCreate(
                detection_id=detection_id,
                severity=severity,
                message=message
            )

            self.db_service.create_alert(alert_create)

            self.logger.warning(
                f"Created {severity} alert for detection {detection_id}: {message}"
            )

        except Exception as e:
            self.logger.error(f"Error creating non-compliance alert: {e}")

    def _calculate_alert_severity(self, result: DetectionResult) -> str:
        """
        Calculate alert severity based on detection

        Args:
            result: Detection result

        Returns:
            Severity level (critical, high, medium, low)
        """
        # Count missing required EPIs
        missing_required = 0

        for epi_type, required in self.config.epi_types.items():
            if required.get('required', False) and not result.epis_detected.get(epi_type, False):
                missing_required += 1

        # Determine severity
        if missing_required >= 3:
            return "critical"
        elif missing_required == 2:
            return "high"
        elif missing_required == 1:
            return "medium"
        else:
            return "low"

    def _generate_alert_message(self, result: DetectionResult) -> str:
        """
        Generate alert message from detection result

        Args:
            result: Detection result

        Returns:
            Alert message
        """
        # Find missing EPIs
        missing_epis = []

        for epi_type, required in self.config.epi_types.items():
            if required.get('required', False) and not result.epis_detected.get(epi_type, False):
                epi_label = required.get('label', epi_type)
                missing_epis.append(epi_label)

        # Generate message
        if missing_epis:
            return f"EPIs não detectados: {', '.join(missing_epis)}"
        else:
            return "Detectado possível não conformidade"

    def save_annotated_frame(
        self,
        frame: np.ndarray,
        result: DetectionResult,
        camera_id: int
    ) -> Optional[str]:
        """
        Save annotated frame with bounding boxes and information

        Args:
            frame: Original frame
            result: Detection result
            camera_id: Camera ID

        Returns:
            Path to saved image or None
        """
        try:
            # Create annotated frame
            annotated = self._create_annotated_frame(frame, result)

            # Generate filename
            timestamp = result.timestamp.strftime('%Y%m%d_%H%M%S')
            filename = f"annotated_camera_{camera_id}_{timestamp}.jpg"
            filepath = self.config.annotated_images_dir / filename

            # Save image
            cv2.imwrite(str(filepath), annotated)

            self.logger.debug(f"Saved annotated frame to: {filepath}")

            return str(filepath)

        except Exception as e:
            self.logger.error(f"Error saving annotated frame: {e}")
            return None

    def _create_annotated_frame(
        self,
        frame: np.ndarray,
        result: DetectionResult
    ) -> np.ndarray:
        """
        Create annotated frame with bounding boxes and overlay information

        Args:
            frame: Original frame
            result: Detection result

        Returns:
            Annotated frame
        """
        annotated = frame.copy()

        # Draw bounding boxes
        for bbox in result.detections:
            x1, y1, x2, y2 = int(bbox.x1), int(bbox.y1), int(bbox.x2), int(bbox.y2)

            # Choose color
            color = self._get_color_for_class(bbox.class_name)

            # Draw rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)

            # Add label
            label = f"{bbox.class_name}: {bbox.confidence:.2f}"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)

            cv2.rectangle(
                annotated,
                (x1, y1 - label_size[1] - 10),
                (x1 + label_size[0], y1),
                color,
                -1
            )

            cv2.putText(
                annotated,
                label,
                (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (255, 255, 255),
                2
            )

        # Add info overlay
        self._add_info_overlay(annotated, result)

        return annotated

    def _add_info_overlay(self, frame: np.ndarray, result: DetectionResult):
        """
        Add information overlay to frame

        Args:
            frame: Frame to annotate
            result: Detection result
        """
        # Status box
        status_text = "COMPLIANT" if result.is_compliant else "NON-COMPLIANT"
        status_color = (0, 255, 0) if result.is_compliant else (0, 0, 255)

        # Draw background
        cv2.rectangle(frame, (10, 10), (400, 150), (0, 0, 0), -1)

        # Draw status
        cv2.putText(
            frame,
            f"Status: {status_text}",
            (20, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            status_color,
            2
        )

        # Draw timestamp
        timestamp_text = result.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        cv2.putText(
            frame,
            f"Time: {timestamp_text}",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )

        # Draw EPI status
        y_offset = 100
        for epi_type, detected in result.epis_detected.items():
            epi_status = "✓" if detected else "✗"
            epi_color = (0, 255, 0) if detected else (0, 0, 255)

            cv2.putText(
                frame,
                f"{epi_status} {epi_type}",
                (20, y_offset),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                epi_color,
                2
            )

            y_offset += 25

    def _get_color_for_class(self, class_name: str) -> tuple:
        """
        Get color for class

        Args:
            class_name: Class name

        Returns:
            BGR color tuple
        """
        class_lower = class_name.lower()

        if any(epi in class_lower for epi in ['helmet', 'glove', 'glass', 'vest', 'boot']):
            return (0, 255, 0)  # Green
        elif class_lower == 'person':
            return (255, 0, 0)  # Blue
        else:
            return (0, 0, 255)  # Red

    def generate_compliance_report(
        self,
        camera_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Generate compliance report

        Args:
            camera_id: Camera ID (None for all)
            start_date: Start date
            end_date: End date

        Returns:
            Report dictionary
        """
        try:
            # Get statistics
            stats = self.db_service.get_compliance_stats(start_date, end_date)

            # Get camera stats
            camera_stats = self.db_service.get_camera_stats(camera_id)

            # Get recent alerts
            alerts = self.db_service.get_alerts(unresolved_only=True, limit=20)

            report = {
                "generated_at": datetime.now().isoformat(),
                "period": {
                    "start": start_date.isoformat() if start_date else None,
                    "end": end_date.isoformat() if end_date else None
                },
                "overall_stats": {
                    "total_detections": stats.total_detections,
                    "compliant_detections": stats.compliant_detections,
                    "non_compliant_detections": stats.non_compliant_detections,
                    "compliance_rate": stats.compliance_rate
                },
                "epi_detection_rates": stats.epi_detection_rates,
                "camera_stats": [
                    {
                        "camera_id": cs.camera_id,
                        "camera_name": cs.camera_name,
                        "total_detections": cs.total_detections,
                        "compliance_rate": cs.compliance_rate
                    }
                    for cs in camera_stats
                ],
                "recent_alerts": [
                    {
                        "id": alert.id,
                        "severity": alert.severity,
                        "message": alert.message,
                        "created_at": alert.created_at.isoformat()
                    }
                    for alert in alerts
                ]
            }

            self.logger.info(f"Generated compliance report: {stats.compliance_rate}% compliance")

            return report

        except Exception as e:
            self.logger.error(f"Error generating compliance report: {e}")
            return {}

    def export_report(
        self,
        report: Dict[str, Any],
        format: str = "json",
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Export report to file

        Args:
            report: Report dictionary
            format: Export format (json, csv)
            output_path: Output file path

        Returns:
            Path to exported file or None
        """
        try:
            if output_path is None:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                output_path = str(self.config.reports_dir / f"compliance_report_{timestamp}.{format}")

            output_path = Path(output_path)

            if format == "json":
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(report, f, indent=2, ensure_ascii=False)

            elif format == "csv":
                import pandas as pd

                # Flatten report for CSV
                flat_data = []

                for camera_stat in report.get("camera_stats", []):
                    flat_data.append({
                        "camera_id": camera_stat["camera_id"],
                        "camera_name": camera_stat["camera_name"],
                        "total_detections": camera_stat["total_detections"],
                        "compliance_rate": camera_stat["compliance_rate"]
                    })

                df = pd.DataFrame(flat_data)
                df.to_csv(output_path, index=False)

            else:
                raise ValueError(f"Unsupported format: {format}")

            self.logger.info(f"Exported report to: {output_path}")

            return str(output_path)

        except Exception as e:
            self.logger.error(f"Error exporting report: {e}")
            return None


def get_annotation_agent() -> AnnotationAgent:
    """
    Get or create annotation agent instance

    Returns:
        AnnotationAgent: Annotation agent instance
    """
    return AnnotationAgent()
