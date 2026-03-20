"""
API Server for EPI Recognition System
Receives images from frontend and returns YOLO detections
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import numpy as np
from cv2 import imdecode, IMREAD_COLOR
from pathlib import Path

from services.yolo_service import YOLOService
from utils.logger import get_logger

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend
logger = get_logger(__name__)

# Initialize YOLO service
try:
    yolo_service = YOLOService()
    logger.info("✅ YOLO service initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize YOLO service: {e}")
    yolo_service = None


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'yolo_loaded': yolo_service is not None
    })


@app.route('/api/detect', methods=['POST'])
def detect_objects():
    """
    Detect objects in image

    Expects JSON:
    {
        "image": "base64_encoded_image_data",
        "camera_id": 1
    }

    Returns:
    {
        "success": true,
        "detections": [
            {
                "class": "person",
                "confidence": 0.92,
                "bbox": [x1, y1, x2, y2]
            }
        ]
    }
    """
    try:
        # Get request data
        data = request.get_json()

        if not data or 'image' not in data:
            return jsonify({
                'success': False,
                'error': 'No image data provided'
            }), 400

        # Decode base64 image
        image_data = data['image']
        if ',' in image_data:
            # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
            image_data = image_data.split(',')[1]

        # Decode base64 to bytes
        image_bytes = base64.b64decode(image_data)

        # Convert to numpy array
        nparr = np.frombuffer(image_bytes, np.uint8)

        # Decode image
        image = imdecode(nparr, IMREAD_COLOR)

        if image is None:
            return jsonify({
                'success': False,
                'error': 'Failed to decode image'
            }), 400

        logger.info(f"📸 Image received: {image.shape[1]}x{image.shape[0]}")

        # Check if YOLO service is available
        if yolo_service is None:
            return jsonify({
                'success': False,
                'error': 'YOLO service not available'
            }), 503

        # Perform detection
        detections = yolo_service.detect(image)

        # Format detections for frontend
        formatted_detections = []
        for det in detections:
            formatted_detections.append({
                'class': det.class_name,
                'confidence': float(det.confidence),
                'bbox': [
                    float(det.x1),
                    float(det.y1),
                    float(det.x2),
                    float(det.y2)
                ]
            })

        logger.info(f"✅ Detected {len(formatted_detections)} objects")

        return jsonify({
            'success': True,
            'detections': formatted_detections
        })

    except Exception as e:
        logger.error(f"❌ Error during detection: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/test', methods=['GET'])
def test_detection():
    """Test endpoint to verify API is working"""
    return jsonify({
        'message': 'API is working!',
        'yolo_loaded': yolo_service is not None,
        'endpoints': {
            'health': 'GET /health',
            'detect': 'POST /api/detect',
            'test': 'GET /api/test'
        }
    })


if __name__ == '__main__':
    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║   EPI Recognition API Server                          ║
    ║   http://localhost:5001                               ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    logger.info("🚀 Starting API server on http://localhost:5001")
    logger.info("📡 Endpoints:")
    logger.info("   GET  /health")
    logger.info("   GET  /api/test")
    logger.info("   POST /api/detect")

    app.run(
        host='0.0.0.0',
        port=5001,
        debug=True
    )
