"""
OCR Service Wrapper - Safe import without pytesseract dependency
"""
try:
    from backend.ocr_service import OCRService
    OCR_AVAILABLE = True
except ImportError:
    # pytesseract não disponível
    OCR_AVAILABLE = False
    
    class OCRService:
        """Mock OCR service when pytesseract is not available"""
        def __init__(self):
            pass
        
        def process_image(self, *args, **kwargs):
            return {"error": "OCR not available - pytesseract not installed"}
        
        def extract_text(self, *args, **kwargs):
            return ""
