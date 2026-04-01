"""
Video Processor Wrapper - Safe import without cv2/ultralytics dependencies
"""
try:
    from backend.video_processor import VideoProcessor
    VIDEO_PROCESSOR_AVAILABLE = True
except ImportError:
    # cv2 ou outras deps não disponíveis
    VIDEO_PROCESSOR_AVAILABLE = False
    
    class VideoProcessor:
        """Mock video processor when cv2 is not available"""
        def __init__(self):
            pass

        def process_video(self, *args, **kwargs):
            return {"success": False, "error": "Video processing not available - cv2 not installed"}

        def extract_frames(self, *args, **kwargs):
            return {"success": False, "error": "Frame extraction not available - cv2 not installed"}
