"""
API Server for EPI Recognition System - SIMPLIFICADO
Receives images from frontend and returns YOLO detections
NO SYSTEM LEGACY - Only YOLO and Flask
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import numpy as np
import os
from cv2 import imdecode, IMREAD_COLOR
from ultralytics import YOLO

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for frontend

# Load YOLO model
model_path = 'models/yolov8n.pt'
try:
    print(f"Loading YOLO model from: {model_path}")
    model = YOLO(model_path)
    print("✅ YOLO model loaded successfully")
except Exception as e:
    print(f"❌ Failed to load YOLO model: {e}")
    model = None


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'yolo_loaded': model is not None
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
            # Remove data URL prefix if present
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

        print(f"📸 Image received: {image.shape[1]}x{image.shape[0]}")

        # Check if YOLO is available
        if model is None:
            return jsonify({
                'success': False,
                'error': 'YOLO model not available'
            }), 503

        # Perform detection
        results = model(image, conf=0.25, verbose=False)

        # Format detections for frontend
        detections = []
        if results and len(results) > 0:
            result = results[0]
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Get box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

                    # Get confidence and class
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = result.names[class_id]

                    detections.append({
                        'class': class_name,
                        'confidence': float(confidence),
                        'bbox': [
                            float(x1),
                            float(y1),
                            float(x2),
                            float(y2)
                        ]
                    })

        print(f"✅ Detected {len(detections)} objects")

        return jsonify({
            'success': True,
            'detections': detections
        })

    except Exception as e:
        print(f"❌ Error during detection: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/test', methods=['GET'])
def test_detection():
    """Test endpoint"""
    return jsonify({
        'message': 'API is working!',
        'yolo_loaded': model is not None,
        'endpoints': {
            'health': 'GET /health',
            'detect': 'POST /api/detect',
            'test': 'GET /api/test'
        }
    })


if __name__ == '__main__':
    # Get port from environment variable (Railway sets this) or default to 5001
    port = int(os.environ.get('PORT', 5001))

    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║   EPI Recognition API Server (SIMPLIFICADO)             ║
    ║   Railway Deployment                                      ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    print("🚀 Starting API server...")
    print(f"📡 Port: {port}")
    print("📡 Endpoints:")
    print("   GET  /health")
    print("   GET  /api/test")
    print("   POST /api/detect")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # Production mode
    )
