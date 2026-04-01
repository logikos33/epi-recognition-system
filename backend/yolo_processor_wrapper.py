"""
YOLO Processor Wrapper - Safe import without ultralytics/cv2 dependencies
"""
try:
    from backend.yolo_processor import YOLOProcessorManager
    YOLO_AVAILABLE = True
except ImportError:
    # ultralytics, cv2 ou outras deps não disponíveis
    YOLO_AVAILABLE = False
    
    class YOLOProcessorManager:
        """Mock manager when YOLO is not available"""
        def __init__(self):
            self.model = None

        def set_model(self, model):
            pass

        def set_detection_callback(self, callback):
            """Set callback for detection results - mock version"""
            pass

        def start_processing(self, *args, **kwargs):
            pass

        def stop_processing(self, *args, **kwargs):
            pass

        def get_active_cameras(self):
            """Return list of active cameras - mock version for API"""
            return []  # Empty list since YOLO not available in API

        def start_processor(self, camera_id, rtsp_url, fps):
            """Start YOLO processor for camera - mock version for API"""
            pass

        def stop_processor(self, camera_id):
            """Stop YOLO processor for camera - mock version for API"""
            pass

        def is_processor_running(self, camera_id):
            """Check if processor is running - mock version for API"""
            return False  # Always False since YOLO not available in API
