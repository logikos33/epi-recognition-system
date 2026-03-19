"""
EPI Recognition System - Main Entry Point
"""
import asyncio
import argparse
import sys
from pathlib import Path
from datetime import datetime

from agents.orchestrator_agent import OrchestratorAgent, get_orchestrator_agent
from agents.recognition_agent import RecognitionAgent, get_recognition_agent
from services.camera_service import CameraService, get_camera_service
from services.database_service import DatabaseService, get_database_service
from utils.logger import get_logger
from utils.config import get_config


class EPISystem:
    """
    Main EPI Recognition System class
    """

    def __init__(self):
        """Initialize the EPI system"""
        self.logger = get_logger(__name__)
        self.config = get_config()

        # Initialize services
        self.orchestrator = get_orchestrator_agent()
        self.database = get_database_service()
        self.camera_service = get_camera_service()

        self.logger.info(f"EPI Recognition System v{self.config.app_version} initialized")

    def start(self):
        """Start the system"""
        try:
            self.logger.info("Starting EPI Recognition System...")

            # Start all agents
            success = self.orchestrator.start_all_agents()

            if success:
                self.logger.info("System started successfully")
                return True
            else:
                self.logger.error("Failed to start system")
                return False

        except Exception as e:
            self.logger.error(f"Error starting system: {e}")
            return False

    def stop(self):
        """Stop the system"""
        try:
            self.logger.info("Stopping EPI Recognition System...")

            # Stop all agents
            success = self.orchestrator.stop_all_agents()

            if success:
                self.logger.info("System stopped successfully")
                return True
            else:
                self.logger.error("Failed to stop system")
                return False

        except Exception as e:
            self.logger.error(f"Error stopping system: {e}")
            return False

    def run_camera_pipeline(
        self,
        camera_id: int,
        duration: int = 60
    ):
        """
        Run pipeline for a specific camera

        Args:
            camera_id: Camera ID
            duration: Duration in seconds
        """
        try:
            self.logger.info(f"Running pipeline for camera {camera_id} for {duration} seconds")

            # Add camera if needed (for testing with webcam)
            if camera_id not in self.camera_service.cameras:
                self.camera_service.add_camera(
                    camera_id=camera_id,
                    source_url=str(camera_id),  # Webcam ID
                    name=f"Webcam {camera_id}",
                    location="Test Location"
                )

            # Start camera
            self.camera_service.start_camera(camera_id)

            # Run for specified duration
            stats = self.orchestrator.run_pipeline_for_duration(camera_id, duration)

            # Stop camera
            self.camera_service.stop_camera(camera_id)

            self.logger.info(f"Pipeline completed: {stats}")

            return stats

        except Exception as e:
            self.logger.error(f"Error running camera pipeline: {e}")
            return None

    def add_camera(
        self,
        name: str,
        location: str,
        rtsp_url: str
    ) -> int:
        """
        Add a new camera to the system

        Args:
            name: Camera name
            location: Camera location
            rtsp_url: RTSP URL

        Returns:
            Camera ID
        """
        return self.orchestrator.add_camera(name, location, rtsp_url)

    def list_cameras(self):
        """List all cameras in the system"""
        cameras = self.database.get_all_cameras(active_only=True)

        self.logger.info(f"Active cameras ({len(cameras)}):")

        for camera in cameras:
            self.logger.info(f"  - {camera.name} ({camera.location})")

        return cameras

    def get_system_status(self):
        """Get current system status"""
        return self.orchestrator.get_system_status()

    def run_dashboard(self):
        """Run the Streamlit dashboard"""
        import subprocess

        dashboard_path = Path(__file__).parent / "agents" / "reporting_agent" / "dashboard_main.py"

        self.logger.info(f"Starting dashboard at: {dashboard_path}")

        try:
            subprocess.run([
                "streamlit", "run", str(dashboard_path),
                "--server.port", str(self.config.streamlit_port),
                "--server.address", self.config.streamlit_host
            ])

        except Exception as e:
            self.logger.error(f"Error starting dashboard: {e}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="EPI Recognition System - Sistema de Monitoramento de EPI"
    )

    # Main command
    parser.add_argument(
        "command",
        choices=["start", "stop", "test", "camera", "dashboard", "status"],
        help="Command to execute"
    )

    # Optional arguments
    parser.add_argument("--camera-id", type=int, help="Camera ID")
    parser.add_argument("--duration", type=int, default=60, help="Duration in seconds")
    parser.add_argument("--name", type=str, help="Camera name")
    parser.add_argument("--location", type=str, help="Camera location")
    parser.add_argument("--rtsp-url", type=str, help="RTSP URL")
    parser.add_argument("--image", type=str, help="Image path for testing")
    parser.add_argument("--video", type=str, help="Video path for testing")

    args = parser.parse_args()

    # Create system instance
    system = EPISystem()

    # Execute command
    if args.command == "start":
        """Start the monitoring system"""
        if system.start():
            print("✅ System started successfully")
            print("Press Ctrl+C to stop...")

            try:
                # Keep running
                import time
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping system...")
                system.stop()

        else:
            print("❌ Failed to start system")
            sys.exit(1)

    elif args.command == "stop":
        """Stop the monitoring system"""
        if system.stop():
            print("✅ System stopped successfully")
        else:
            print("❌ Failed to stop system")
            sys.exit(1)

    elif args.command == "camera":
        """Run pipeline for a specific camera"""
        if not args.camera_id:
            print("❌ Error: --camera-id is required for camera command")
            sys.exit(1)

        stats = system.run_camera_pipeline(args.camera_id, args.duration)

        if stats:
            print("✅ Pipeline completed successfully")
            print(f"Frames processed: {stats['frames_processed']}")
            print(f"Detections: {stats['detections']}")
            print(f"Compliance rate: {stats['compliance_rate']:.2f}%")
        else:
            print("❌ Failed to run camera pipeline")
            sys.exit(1)

    elif args.command == "test":
        """Test system components"""
        print("🧪 Testing system components...")

        # Test 1: Image detection
        if args.image:
            print(f"\n📸 Testing image detection: {args.image}")

            recognition_agent = get_recognition_agent()

            result = recognition_agent.detect_epis(args.image, save_annotated=True)

            if result:
                print(f"✅ Detection successful")
                print(f"   Compliant: {result.is_compliant}")
                print(f"   Persons: {result.person_count}")
                print(f"   EPIs detected: {result.epis_detected}")
                print(f"   Confidence: {result.confidence:.2f}")
            else:
                print(f"❌ Detection failed")

        # Test 2: Video processing
        elif args.video:
            print(f"\n🎥 Testing video processing: {args.video}")

            recognition_agent = get_recognition_agent()

            results = recognition_agent.detect_epis_in_video(args.video, frame_interval=30)

            if results:
                stats = recognition_agent.get_detection_statistics(results)
                print(f"✅ Video processing successful")
                print(f"   Total detections: {stats['total_detections']}")
                print(f"   Compliance rate: {stats['compliance_rate']:.2f}%")
            else:
                print(f"❌ Video processing failed")

        else:
            print("ℹ️  Please specify --image or --video for testing")
            print("   Example: python main.py test --image test_image.jpg")

    elif args.command == "dashboard":
        """Run the Streamlit dashboard"""
        system.run_dashboard()

    elif args.command == "status":
        """Get system status"""
        status = system.get_system_status()

        print("\n📊 System Status")
        print("=" * 50)

        if status["is_running"]:
            print(f"✅ Status: Running")
            print(f"📹 Active cameras: {status['active_cameras']}/{status['total_cameras']}")
            print(f"⏱️  Uptime: {status['stats']['uptime']}")
            print(f"🔍 Total detections: {status['stats']['total_detections']}")
            print(f"✅ Compliance rate: {status['stats']['compliance_rate']:.2f}%")
        else:
            print(f"❌ Status: Stopped")

        print("=" * 50)

        # List cameras
        if status["cameras"]:
            print("\n📹 Cameras:")
            for camera in status["cameras"]:
                status_icon = "✅" if camera["is_running"] else "❌"
                print(f"  {status_icon} {camera['name']} ({camera['location']})")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
