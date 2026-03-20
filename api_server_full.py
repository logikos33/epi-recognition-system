"""
API Server for EPI Recognition System - FULL VERSION
With Authentication, Database, and YOLO Detection
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import base64
import numpy as np
import os
from cv2 import imdecode, IMREAD_COLOR
from ultralytics import YOLO
import bcrypt
import jwt
import datetime
from datetime import timedelta, timezone
import uuid
import re

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
DB_URL = os.environ.get('DATABASE_URL', '')

# Load YOLO model
model_path = 'models/yolov8n.pt'
try:
    print(f"Loading YOLO model from: {model_path}")
    model = YOLO(model_path)
    print("✅ YOLO model loaded successfully")
except Exception as e:
    print(f"❌ Failed to load YOLO model: {e}")
    model = None


# ============================================
# AUTHENTICATION HELPERS
# ============================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_token(user_id: str, email: str) -> str:
    """Create JWT token"""
    payload = {
        'user_id': str(user_id),
        'email': email,
        'exp': datetime.datetime.now(timezone.utc) + timedelta(days=7),
        'iat': datetime.datetime.now(timezone.utc)
    }
    return jwt.encode(payload, SECRET_KEY, algorithm='HS256')

def verify_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ============================================
# MOCK DATABASE (Replace with real DB connection)
# ============================================

# Mock users storage (in production, use PostgreSQL/Supabase)
mock_users = {}
mock_detections = []

# ============================================
# AUTH ENDPOINTS
# ============================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    Register new user

    Expects:
    {
        "email": "user@example.com",
        "password": "password123",
        "full_name": "John Doe",
        "company_name": "ACME Corp"
    }
    """
    try:
        data = request.get_json()

        # Validate input
        if not data or not all(k in data for k in ['email', 'password']):
            return jsonify({'success': False, 'error': 'Email and password required'}), 400

        email = data['email'].lower().strip()
        password = data['password']
        full_name = data.get('full_name', '')
        company_name = data.get('company_name', '')

        # Validate email format
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            return jsonify({'success': False, 'error': 'Invalid email format'}), 400

        # Validate password length
        if len(password) < 6:
            return jsonify({'success': False, 'error': 'Password must be at least 6 characters'}), 400

        # Check if user already exists
        if email in mock_users:
            return jsonify({'success': False, 'error': 'User already exists'}), 409

        # Create new user
        user_id = str(uuid.uuid4())
        password_hash = hash_password(password)

        mock_users[email] = {
            'id': user_id,
            'email': email,
            'password_hash': password_hash,
            'full_name': full_name,
            'company_name': company_name,
            'created_at': datetime.datetime.now().isoformat()
        }

        # Generate token
        token = create_token(user_id, email)

        return jsonify({
            'success': True,
            'message': 'User registered successfully',
            'token': token,
            'user': {
                'id': user_id,
                'email': email,
                'full_name': full_name,
                'company_name': company_name
            }
        }), 201

    except Exception as e:
        print(f"❌ Registration error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Login user

    Expects:
    {
        "email": "user@example.com",
        "password": "password123"
    }
    """
    try:
        data = request.get_json()

        if not data or not all(k in data for k in ['email', 'password']):
            return jsonify({'success': False, 'error': 'Email and password required'}), 400

        email = data['email'].lower().strip()
        password = data['password']

        # Find user
        user = mock_users.get(email)
        if not user:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

        # Verify password
        if not verify_password(password, user['password_hash']):
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

        # Generate token
        token = create_token(user['id'], user['email'])

        return jsonify({
            'success': True,
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user.get('full_name', ''),
                'company_name': user.get('company_name', '')
            }
        }), 200

    except Exception as e:
        print(f"❌ Login error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/verify', methods=['POST'])
def verify_auth():
    """
    Verify JWT token

    Expects:
    {
        "token": "jwt_token_here"
    }
    """
    try:
        data = request.get_json()
        if not data or 'token' not in data:
            return jsonify({'success': False, 'error': 'Token required'}), 400

        token = data['token']
        payload = verify_token(token)

        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Get user info
        user = mock_users.get(payload['email'])
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user.get('full_name', ''),
                'company_name': user.get('company_name', '')
            }
        }), 200

    except Exception as e:
        print(f"❌ Verify error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/auth/me', methods=['GET'])
def get_current_user():
    """Get current authenticated user"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)

        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        user = mock_users.get(payload['email'])
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user.get('full_name', ''),
                'company_name': user.get('company_name', ''),
                'created_at': user.get('created_at', '')
            }
        }), 200

    except Exception as e:
        print(f"❌ Get user error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# YOLO DETECTION ENDPOINTS (Existing)
# ============================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'yolo_loaded': model is not None,
        'version': '2.0.0'
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
            image_data = image_data.split(',')[1]

        image_bytes = base64.b64decode(image_data)
        nparr = np.frombuffer(image_bytes, np.uint8)
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
                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                    confidence = float(box.conf[0].cpu().numpy())
                    class_id = int(box.cls[0].cpu().numpy())
                    class_name = result.names[class_id]

                    detections.append({
                        'class': class_name,
                        'confidence': float(confidence),
                        'bbox': [float(x1), float(y1), float(x2), float(y2)]
                    })

        print(f"✅ Detected {len(detections)} objects")

        # TODO: Save detection to database
        # save_detection_to_db(user_id, camera_id, detections)

        return jsonify({
            'success': True,
            'detections': detections,
            'total_objects': len(detections)
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
        'version': '2.0.0',
        'yolo_loaded': model is not None,
        'endpoints': {
            'health': 'GET /health',
            'detect': 'POST /api/detect',
            'test': 'GET /api/test',
            'auth': {
                'register': 'POST /api/auth/register',
                'login': 'POST /api/auth/login',
                'verify': 'POST /api/auth/verify',
                'me': 'GET /api/auth/me'
            }
        }
    })


# ============================================
# DETECTION HISTORY ENDPOINTS
# ============================================

@app.route('/api/detections', methods=['GET'])
def get_detections():
    """
    Get detection history

    Query params:
    - user_id: UUID
    - camera_id: UUID (optional)
    - limit: number (default 50)
    - offset: number (default 0)
    """
    try:
        # Get auth token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        user_id = request.args.get('user_id', payload['user_id'])
        limit = int(request.args.get('limit', 50))
        offset = int(request.args.get('offset', 0))

        # TODO: Query from database
        # For now, return mock data
        user_detections = [d for d in mock_detections if d['user_id'] == user_id]

        return jsonify({
            'success': True,
            'detections': user_detections[offset:offset+limit],
            'total': len(user_detections),
            'limit': limit,
            'offset': offset
        }), 200

    except Exception as e:
        print(f"❌ Get detections error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================
# START SERVER
# ============================================

if __name__ == '__main__':
    # Get port from environment variable (Railway sets this) or default to 5001
    port = int(os.environ.get('PORT', 5001))

    print("""
    ╔═══════════════════════════════════════════════════════╗
    ║   EPI Recognition API Server (FULL VERSION)            ║
    ║   Railway Deployment - With Auth & DB                 ║
    ╚═══════════════════════════════════════════════════════╝
    """)

    print("🚀 Starting API server...")
    print(f"📡 Port: {port}")
    print("📡 Endpoints:")
    print("   GET  /health")
    print("   GET  /api/test")
    print("   POST /api/detect")
    print("   POST /api/auth/register")
    print("   POST /api/auth/login")
    print("   POST /api/auth/verify")
    print("   GET  /api/auth/me")
    print("   GET  /api/detections")

    app.run(
        host='0.0.0.0',
        port=port,
        debug=False  # Production mode
    )
