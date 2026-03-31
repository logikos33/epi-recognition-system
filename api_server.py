"""
API Server for EPI Recognition System
With Authentication, Database, YOLO Detection, HLS Streaming, and WebSocket Support
"""
from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
# from flask_socketio import SocketIO, emit, join_room, leave_room  # TODO: Implement WebSocket support
from werkzeug.utils import secure_filename
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
import sys
import logging
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add backend directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Import database modules
from backend.database import get_db, init_db, SessionLocal
from backend.auth_db import (
    create_user, get_user_by_email, get_user_by_id,
    verify_user_credentials, update_last_login, verify_session
)
import backend.auth_db as auth_db

from sqlalchemy import text
from backend.products import ProductService
from backend.training_db import TrainingProjectDB
from backend.camera_service import CameraService  # For fueling monitoring cameras (bays)
from backend.ip_camera_service import IPCameraService  # For IP cameras
from backend.fueling_session_service import FuelingSessionService
from backend.ocr_service import OCRService
from backend.stream_manager import StreamManager
from backend.yolo_processor import YOLOProcessorManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)


# ============================================================================
# Database Session Management with Flask Teardown
# ============================================================================

def get_db_session():
    """Retorna sessão do banco, armazenada no contexto do request.
    Fecha automaticamente no final do request via teardown."""
    if 'db' not in g:
        g.db = SessionLocal()
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    """Fecha a sessão do banco no final de cada request."""
    db = g.pop('db', None)
    if db is not None:
        try:
            if exception:
                db.rollback()
            db.close()
        except Exception:
            pass


# Initialize Flask-SocketIO
# socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=True, engineio_logger=False)  # TODO: Implement WebSocket support
socketio = None

# Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'your-secret-key-change-in-production-min-32-chars!')
DB_URL = os.environ.get('DATABASE_URL', '')
PORT = int(os.environ.get('PORT', 5001))

# Load YOLO model
model_path = 'models/yolov8n.pt'
try:
    logger.info(f"Loading YOLO model from: {model_path}")
    model = YOLO(model_path)
    logger.info("✅ YOLO model loaded successfully")
except Exception as e:
    logger.error(f"❌ Failed to load YOLO model: {e}")
    model = None

# Initialize StreamManager
stream_manager = StreamManager(hls_base_dir='./streams')

# Initialize YOLOProcessorManager
yolo_processor_manager = YOLOProcessorManager()
if model:
    yolo_processor_manager.set_model(model)

# Detection callback for WebSocket broadcasting
def on_detection_result(result: dict):
    """Callback for YOLO detection results - broadcasts via WebSocket"""
    try:
        # Emit to camera-specific room
        room = f"camera_{result['camera_id']}"
        socketio.emit('detection', result, room=room)
        logger.debug(f"📡 Emitted detection to {room}: {len(result.get('detections', []))} objects")
    except Exception as e:
        logger.error(f"❌ Error emitting detection: {e}")

# Register detection callback
yolo_processor_manager.set_detection_callback(on_detection_result)


# ============================================================================
# Authentication Helper Functions
# ============================================================================

def verify_token(token: str) -> dict:
    """Verify JWT token and return payload"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


# ============================================================================
# WebSocket Events
# ============================================================================

# TODO: Implement WebSocket support
# @socketio.on('connect')
# def handle_connect():
#     """Handle WebSocket connection"""
#     logger.info(f"✅ WebSocket client connected: {request.sid}")
#     emit('connected', {'status': 'connected', 'sid': request.sid})
#
#
# @socketio.on('disconnect')
# def handle_disconnect():
#     """Handle WebSocket disconnection"""
#     logger.info(f"❌ WebSocket client disconnected: {request.sid}")
#
#
# @socketio.on('subscribe_camera')
# def handle_subscribe_camera(data):
#     """Subscribe to detection updates for a specific camera"""
#     camera_id = data.get('camera_id')
#     if camera_id is None:
#         emit('error', {'message': 'camera_id required'})
#         return
#
#     room = f"camera_{camera_id}"
#     join_room(room)
#     logger.info(f"📹 Client {request.sid} subscribed to camera {camera_id}")
#     emit('subscribed', {'camera_id': camera_id, 'room': room})
#
#
# @socketio.on('unsubscribe_camera')
# def handle_unsubscribe_camera(data):
#     """Unsubscribe from detection updates for a specific camera"""
#     camera_id = data.get('camera_id')
#     if camera_id is None:
#         emit('error', {'message': 'camera_id required'})
#         return
#
#     room = f"camera_{camera_id}"
#     leave_room(room)
#     logger.info(f"📹 Client {request.sid} unsubscribed from camera {camera_id}")
#     emit('unsubscribed', {'camera_id': camera_id, 'room': room})


# ============================================================================
# Authentication Routes
# ============================================================================

@app.route('/api/auth/register', methods=['POST'])
def register():
    """
    Register a new user.

    Request body:
        - email: User email (required)
        - password: User password (required, min 6 characters)
        - full_name: User's full name (optional)
        - company_name: User's company name (optional)

    Returns:
        JSON with success status, user data, and JWT token
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400

        email = data['email'].strip().lower()
        password = data['password']

        # Validate password length
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400

        # Validate email format
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', email):
            return jsonify({'error': 'Invalid email format'}), 400

        # Create user
        db = get_db_session()
        user = create_user(
            db,
            email=email,
            password=password,
            full_name=data.get('full_name'),
            company_name=data.get('company_name')
        )

        if not user:
            return jsonify({'error': 'Email already exists'}), 409

        # Generate JWT token
        token = jwt.encode({
            'user_id': user['id'],
            'email': user['email'],
            'exp': datetime.datetime.now(datetime.timezone.utc) + timedelta(days=7)
        }, SECRET_KEY, algorithm='HS256')

        logger.info(f"✅ User registered: {email}")

        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user.get('full_name'),
                'company_name': user.get('company_name'),
                'created_at': user.get('created_at')
            },
            'token': token
        }), 201

    except Exception as e:
        logger.error(f"❌ Registration error: {e}")
        return jsonify({'error': 'Registration failed'}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """
    Authenticate user and return JWT token.

    Request body:
        - email: User email (required)
        - password: User password (required)

    Returns:
        JSON with success status, user data, and JWT token
    """
    try:
        data = request.get_json()

        # Validate required fields
        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400

        email = data['email'].strip().lower()
        password = data['password']

        # Verify credentials
        db = get_db_session()
        user = verify_user_credentials(db, email, password)

        if not user:
            return jsonify({'error': 'Invalid email or password'}), 401

        # Update last login
        update_last_login(db, user['id'])

        # Generate JWT token
        token = jwt.encode({
            'user_id': user['id'],
            'email': user['email'],
            'exp': datetime.datetime.now(datetime.timezone.utc) + timedelta(days=7)
        }, SECRET_KEY, algorithm='HS256')

        logger.info(f"✅ User logged in: {email}")

        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user.get('full_name'),
                'company_name': user.get('company_name')
            },
            'token': token
        }), 200

    except Exception as e:
        logger.error(f"❌ Login error: {e}")
        return jsonify({'error': 'Login failed'}), 500


# ============================================================================
# HLS File Serving
# ============================================================================

@app.route('/streams/<int:camera_id>/<path:filename>')
def serve_hls_file(camera_id, filename):
    """
    Serve HLS playlist and segments.

    Args:
        camera_id: Camera identifier
        filename: HLS file name (stream.m3u8 or segment .ts files)

    Returns:
        HLS file content
    """
    # Verify JWT token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization required'}), 401

    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

    # Verify camera ownership
    db = get_db_session()
    try:
        camera = IPCameraService.get_camera_by_id(db, camera_id)
        if not camera:
            return jsonify({'error': 'Camera not found'}), 404

        # Check if user owns this camera
        if camera['user_id'] != user_id:
            return jsonify({'error': 'Access denied'}), 403

    finally:
        db.close()

    # Serve HLS file
    stream_dir = os.path.join('./streams', str(camera_id))
    logger.debug(f"Serving HLS file: {stream_dir}/{filename}")

    try:
        return send_from_directory(stream_dir, filename)
    except FileNotFoundError:
        return jsonify({'error': 'HLS file not found'}), 404


# ============================================================================
# Stream Management Endpoints
# ============================================================================

@app.route('/api/cameras/<int:camera_id>/stream/start', methods=['POST'])
def start_stream(camera_id):
    """
    Start HLS stream for a camera.

    Request body:
        fps (optional): Detection FPS (default 5)
    """
    # Verify JWT token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization required'}), 401

    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

    # Get camera details
    db = get_db_session()
    try:
        camera = IPCameraService.get_camera_by_id(db, camera_id)
        if not camera:
            return jsonify({'error': 'Camera not found'}), 404

        if camera['user_id'] != user_id:
            return jsonify({'error': 'Access denied'}), 403

        rtsp_url = camera['rtsp_url']
        if not rtsp_url:
            return jsonify({'error': 'Camera has no RTSP URL configured'}), 400

    finally:
        db.close()

    # Start HLS stream
    if stream_manager is None:
        return jsonify({'error': 'Stream manager not implemented'}), 501

    stream_result = stream_manager.start_stream(camera_id, rtsp_url)
    if stream_result['status'] == 'error':
        return jsonify(stream_result), 500

    # Start YOLO processor
    fps = request.json.get('fps', 5) if request.json else 5
    yolo_result = yolo_processor_manager.start_processor(camera_id, rtsp_url, fps)

    if not yolo_result:
        # If YOLO fails, stop HLS stream too
        stream_manager.stop_stream(camera_id)
        return jsonify({'error': 'Failed to start YOLO processor'}), 500

    return jsonify({
        'status': 'started',
        'hls_url': stream_result['hls_url'],
        'camera_id': camera_id,
        'detection_fps': fps
    })


@app.route('/api/cameras/<int:camera_id>/stream/stop', methods=['POST'])
def stop_stream(camera_id):
    """Stop HLS stream and YOLO detection for a camera."""
    # Verify JWT token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization required'}), 401

    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        user_id = payload.get('user_id')
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

    # Stop HLS stream
    if stream_manager is not None:
        stream_manager.stop_stream(camera_id)

    # Stop YOLO processor
    yolo_processor_manager.stop_processor(camera_id)

    return jsonify({
        'status': 'stopped',
        'camera_id': camera_id
    })


@app.route('/api/cameras/<int:camera_id>/stream/status', methods=['GET'])
def get_stream_status(camera_id):
    """Get status of HLS stream and YOLO detection for a camera."""
    # Verify JWT token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization required'}), 401

    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

    # Get stream status
    stream_status = stream_manager.get_stream_status(camera_id) if stream_manager else {'status': 'not_implemented'}

    # Get YOLO processor status
    yolo_active = yolo_processor_manager.is_processor_running(camera_id)

    return jsonify({
        'camera_id': camera_id,
        'stream': stream_status,
        'detection': {
            'active': yolo_active
        }
    })


@app.route('/api/streams/status', methods=['GET'])
def get_all_streams_status():
    """Get status of all active streams and detections."""
    # Verify JWT token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization required'}), 401

    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

    # Get all stream statuses
    stream_statuses = stream_manager.get_all_streams_status() if stream_manager else {}

    # Get all YOLO processor statuses
    active_cameras = yolo_processor_manager.get_active_cameras()

    return jsonify({
        'streams': stream_statuses,
        'detections': {
            'total_active': len(active_cameras),
            'active_cameras': active_cameras
        }
    })


@app.route('/streams/health', methods=['GET'])
def get_streams_health():
    """
    Get detailed health report for all streams (Task 18).

    Returns:
        JSON with detailed health metrics for all active streams including:
        - is_healthy status
        - Process PID
        - Uptime in seconds
        - Restart count
        - Last health check timestamp
    """
    # Verify JWT token
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'error': 'Authorization required'}), 401

    token = auth_header.split(' ')[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    except jwt.ExpiredSignatureError:
        return jsonify({'error': 'Token expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'error': 'Invalid token'}), 401

    # Get health report from stream manager
    if stream_manager:
        health_report = stream_manager.get_stream_health_report()
        return jsonify(health_report)
    else:
        return jsonify({
            'total_streams': 0,
            'streams': [],
            'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
        })


# ============================================================================
# Camera Management Endpoints (IP Cameras)
# ============================================================================

@app.route('/api/cameras', methods=['GET'])
def list_cameras():
    """
    List all cameras for authenticated user

    Returns:
        JSON with success status and list of cameras
    """
    db = None
    try:
        # Get auth token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Get database session
        db = get_db_session()

        # List cameras for user
        cameras = IPCameraService.list_cameras_by_user(db, payload['user_id'])

        return jsonify({
            'success': True,
            'cameras': cameras,
            'count': len(cameras)
        }), 200

    except Exception as e:
        logger.error(f"❌ List cameras error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/cameras', methods=['POST'])
def create_camera():
    """
    Create a new IP camera

    Expects:
    {
        "name": "Camera Name",
        "manufacturer": "intelbras|hikvision|generic",
        "ip": "192.168.1.100",
        "port": 554,
        "username": "admin",
        "password": "password123",
        "channel": 1,
        "subtype": 1,
        "type": "ip",
        "rtsp_url": "rtsp://..."  // optional, auto-generated if not provided
    }

    Returns:
        JSON with success status and created camera
    """
    db = None
    try:
        # Get auth token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Request body is required'}), 400

        # Validate required fields
        required_fields = ['name', 'manufacturer', 'ip']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'{field} is required'}), 400

        # Get database session
        db = get_db_session()

        # Create camera
        camera = IPCameraService.create_camera(
            db,
            user_id=payload['user_id'],
            name=data['name'],
            manufacturer=data['manufacturer'],
            ip=data['ip'],
            port=data.get('port', 554),
            username=data.get('username'),
            password=data.get('password'),
            channel=data.get('channel', 1),
            subtype=data.get('subtype', 1),
            rtsp_url=data.get('rtsp_url'),
            type=data.get('type', 'ip'),
            is_active=data.get('is_active', True)
        )

        if not camera:
            return jsonify({'success': False, 'error': 'Failed to create camera'}), 500

        return jsonify({
            'success': True,
            'camera': camera
        }), 201

    except Exception as e:
        logger.error(f"❌ Create camera error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/cameras/<int:camera_id>', methods=['GET'])
def get_camera(camera_id):
    """
    Get camera by ID

    Args:
        camera_id: Camera ID

    Returns:
        JSON with success status and camera data
    """
    db = None
    try:
        # Get auth token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Get database session
        db = get_db_session()

        # Get camera
        camera = IPCameraService.get_camera_by_id(db, camera_id)

        if not camera:
            return jsonify({'success': False, 'error': 'Camera not found'}), 404

        # Verify user owns this camera
        if camera['user_id'] != payload['user_id']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        return jsonify({
            'success': True,
            'camera': camera
        }), 200

    except Exception as e:
        logger.error(f"❌ Get camera error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/cameras/<int:camera_id>', methods=['PUT'])
def update_camera(camera_id):
    """
    Update camera details

    Args:
        camera_id: Camera ID

    Expects:
    {
        "name": "New Name",
        "ip": "192.168.1.101",
        ... (any camera field)
    }

    Returns:
        JSON with success status and updated camera
    """
    db = None
    try:
        # Get auth token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Request body is required'}), 400

        # Get database session
        db = get_db_session()

        # Verify camera exists and user owns it
        existing_camera = IPCameraService.get_camera_by_id(db, camera_id)
        if not existing_camera:
            return jsonify({'success': False, 'error': 'Camera not found'}), 404

        if existing_camera['user_id'] != payload['user_id']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        # Update camera
        camera = IPCameraService.update_camera(
            db,
            camera_id=camera_id,
            name=data.get('name'),
            manufacturer=data.get('manufacturer'),
            ip=data.get('ip'),
            port=data.get('port'),
            username=data.get('username'),
            password=data.get('password'),
            channel=data.get('channel'),
            subtype=data.get('subtype'),
            rtsp_url=data.get('rtsp_url'),
            type=data.get('type'),
            is_active=data.get('is_active')
        )

        if not camera:
            return jsonify({'success': False, 'error': 'Failed to update camera'}), 500

        return jsonify({
            'success': True,
            'camera': camera
        }), 200

    except Exception as e:
        logger.error(f"❌ Update camera error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/cameras/<int:camera_id>', methods=['DELETE'])
def delete_camera(camera_id):
    """
    Delete camera

    Args:
        camera_id: Camera ID

    Returns:
        JSON with success status
    """
    db = None
    try:
        # Get auth token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Get database session
        db = get_db_session()

        # Verify camera exists and user owns it
        existing_camera = IPCameraService.get_camera_by_id(db, camera_id)
        if not existing_camera:
            return jsonify({'success': False, 'error': 'Camera not found'}), 404

        if existing_camera['user_id'] != payload['user_id']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        # Delete camera
        deleted = IPCameraService.delete_camera(db, camera_id)

        if not deleted:
            return jsonify({'success': False, 'error': 'Failed to delete camera'}), 500

        return jsonify({
            'success': True,
            'message': 'Camera deleted successfully'
        }), 200

    except Exception as e:
        logger.error(f"❌ Delete camera error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/cameras/test', methods=['POST'])
def test_camera_connection():
    """
    Test RTSP connection before saving camera

    Expects:
    {
        "rtsp_url": "rtsp://192.168.1.100:554/stream"
        OR
        {
            "manufacturer": "intelbras",
            "ip": "192.168.1.100",
            "port": 554,
            "username": "admin",
            "password": "password123",
            "channel": 1,
            "subtype": 1
        }
    }

    Returns:
        JSON with connection test result
    """
    try:
        # Get auth token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Request body is required'}), 400

        # Build RTSP URL if not provided directly
        rtsp_url = data.get('rtsp_url')
        if not rtsp_url:
            # Build RTSP URL from components
            from backend.rtsp_builder import RTSPBuilder
            rtsp_url = RTSPBuilder.build_url({
                'manufacturer': data.get('manufacturer', 'generic'),
                'ip': data.get('ip'),
                'port': data.get('port', 554),
                'username': data.get('username', ''),
                'password': data.get('password', ''),
                'channel': data.get('channel', 1),
                'subtype': data.get('subtype', 1)
            })

        # Test connection using ffprobe
        import subprocess
        try:
            # Run ffprobe to test connection (5 second timeout)
            result = subprocess.run(
                [
                    'ffprobe',
                    '-v', 'error',
                    '-show_entries', 'stream=codec_type,width,height',
                    '-of', 'json',
                    '-timeout', '5000000',  # 5 seconds in microseconds
                    '-rtsp_transport', 'tcp',
                    rtsp_url
                ],
                capture_output=True,
                text=True,
                timeout=10  # Python timeout
            )

            if result.returncode == 0:
                # Connection successful
                return jsonify({
                    'success': True,
                    'connected': True,
                    'message': 'Successfully connected to camera',
                    'rtsp_url': rtsp_url
                }), 200
            else:
                # Connection failed
                error_msg = result.stderr.strip() or 'Connection failed'
                return jsonify({
                    'success': True,  # API call succeeded, but connection failed
                    'connected': False,
                    'message': f'Connection failed: {error_msg}',
                    'rtsp_url': rtsp_url
                }), 200

        except subprocess.TimeoutExpired:
            return jsonify({
                'success': True,
                'connected': False,
                'message': 'Connection timeout - camera did not respond within 10 seconds',
                'rtsp_url': rtsp_url
            }), 200
        except FileNotFoundError:
            return jsonify({
                'success': False,
                'connected': False,
                'message': 'ffprobe not found - please install FFmpeg'
            }), 500
        except Exception as e:
            return jsonify({
                'success': True,
                'connected': False,
                'message': f'Error testing connection: {str(e)}',
                'rtsp_url': rtsp_url
            }), 200

    except Exception as e:
        logger.error(f"❌ Test camera connection error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Health Check
# ============================================================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.datetime.now(timezone.utc).isoformat(),
        'services': {
            'yolo_model': model is not None,
            'websocket': True,
            'hls_streaming': True,
            'active_streams': len(stream_manager.active_streams),
            'active_detections': len(yolo_processor_manager.get_active_cameras())
        }
    })


# ============================================================================
# WebSocket Test Endpoint
# ============================================================================

@app.route('/ws/test', methods=['GET'])
def websocket_test():
    """Test endpoint to verify WebSocket support"""
    return jsonify({
        'websocket': 'enabled',
        'endpoint': 'ws://localhost:5001/socket.io/',
        'rooms': ['camera_<id>'],
        'events': ['connect', 'disconnect', 'subscribe_camera', 'unsubscribe_camera', 'detection']
    })


# ============================================================================

# ============================================================================
# Training Video Upload & Processing Endpoints
# ============================================================================

import threading
import os

from backend.video_processor import VideoProcessor


@app.route('/api/training/projects/<project_id>/videos', methods=['POST'])
def upload_training_video(project_id: str):
    """
    Upload a video to a training project and automatically start frame extraction.

    Request: multipart/form-data with 'video' file
    Response: JSON with video_id and status
    """
    try:
        # Verify authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        user_id = payload['user_id']

        # Verify project ownership
        db = get_db_session()
        project_check = db.execute(text("""
            SELECT id FROM training_projects WHERE id = :project_id AND user_id = :user_id
        """), {'project_id': project_id, 'user_id': user_id}).fetchone()

        if not project_check:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        # Check if file exists
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No video file provided'}), 400

        file = request.files['video']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        # Validate file
        if not file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            return jsonify({'success': False, 'error': 'Invalid file format. Use MP4, AVI, MOV or MKV'}), 400

        # Save temp file
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_file:
            file.save(tmp_file.name)
            tmp_path = tmp_file.name

        # Process video (extract metadata, save to DB)
        processor = VideoProcessor()
        result = processor.process_video(
            db=db,
            project_id=project_id,
            user_id=user_id,
            video_path=tmp_path,
            filename=file.filename
        )

        if not result.get('success'):
            os.unlink(tmp_path)  # Clean up on error
            return jsonify(result), 500

        video_id = result['video']['id']
        storage_path = result['video']['storage_path']  # Get permanent path
        logger.info(f"✅ Video uploaded: {file.filename} -> {video_id}")
        logger.info(f"✅ Video stored at: {storage_path}")

        # Clean up temp file (after video was copied to storage)
        os.unlink(tmp_path)

        # Start auto-extraction in background thread
        def auto_extract_background(video_id, video_path, user_id):
            """
            Thread de extração com error handling completo e logging detalhado.

            Args:
                video_id: ID do vídeo no banco
                video_path: Caminho absoluto do arquivo de vídeo
                user_id: ID do usuário para verificação
            """
            import traceback
            logger.info(f"[EXTRACT] ========================================")
            logger.info(f"[EXTRACT] Iniciando extração do vídeo {video_id}")
            logger.info(f"[EXTRACT] Path: {video_path}")

            # Criar NOVA conexão com banco (thread safety)
            from backend.database import SessionLocal
            db_local = SessionLocal()

            try:
                # 1. Verificar se arquivo existe
                if not os.path.exists(video_path):
                    logger.error(f"[EXTRACT] ❌ Arquivo NÃO encontrado: {video_path}")
                    db_local.execute(text("""
                        UPDATE training_videos SET status = 'failed' WHERE id = :video_id
                    """), {'video_id': video_id})
                    db_local.commit()
                    return

                logger.info(f"[EXTRACT] ✅ Arquivo encontrado ({os.path.getsize(video_path)/1024/1024:.1f} MB)")

                # 2. Verificar duplicidade com FOR UPDATE (lock)
                result = db_local.execute(text("""
                    SELECT status, duration_seconds, selected_start, selected_end
                    FROM training_videos WHERE id = :video_id FOR UPDATE
                """), {'video_id': video_id})

                video_data = result.fetchone()
                if not video_data:
                    logger.error(f"[EXTRACT] ❌ Vídeo {video_id} não encontrado no banco")
                    return

                current_status = video_data[0]
                if current_status in ('extracting', 'completed'):
                    logger.info(f"[EXTRACT] ⚠️  Vídeo já está '{current_status}', ignorando")
                    return

                # 3. Marcar como extraindo
                logger.info(f"[EXTRACT] Atualizando status para 'extracting'")
                db_local.execute(text("""
                    UPDATE training_videos
                    SET status = 'extracting', processed_chunks = 0
                    WHERE id = :video_id
                """), {'video_id': video_id})
                db_local.commit()

                # 4. Calcular duração e chunks
                duration = video_data[1] or 60
                start = video_data[2] or 0
                end = video_data[3] or min(duration, 600)
                segment_duration = end - start
                total_chunks = max(1, int(segment_duration / 60) + (1 if segment_duration % 60 > 0 else 0))

                db_local.execute(text("""
                    UPDATE training_videos SET total_chunks = :total WHERE id = :video_id
                """), {'total': total_chunks, 'video_id': video_id})
                db_local.commit()

                logger.info(f"[EXTRACT] Duração: {segment_duration}s ({start}s → {end}s)")
                logger.info(f"[EXTRACT] Chunks: {total_chunks}")

                # 5. Criar diretório de output
                output_base = os.path.join(
                    os.path.dirname(video_path),
                    f"frames_{video_id}"
                )
                os.makedirs(output_base, exist_ok=True)
                logger.info(f"[EXTRACT] Output: {output_base}")

                # 6. Extrair com FFmpeg (paralelo)
                if not shutil.which('ffmpeg'):
                    logger.error("[EXTRACT] ❌ FFmpeg NÃO encontrado!")
                    raise Exception("FFmpeg not found")

                logger.info("[EXTRACT] ✅ FFmpeg encontrado, iniciando extração paralela")
                total_frames = 0
                max_workers = min(4, total_chunks)

                def extract_one_chunk(chunk_num, chunk_start, chunk_duration):
                    """Extrai um chunk usando FFmpeg"""
                    chunk_dir = os.path.join(output_base, f"chunk_{chunk_num:02d}")
                    os.makedirs(chunk_dir, exist_ok=True)

                    cmd = [
                        'ffmpeg', '-y',
                        '-ss', str(chunk_start),
                        '-i', os.path.abspath(video_path),  # PATH ABSOLUTO!
                        '-t', str(min(chunk_duration, 60)),
                        '-vf', 'fps=1,scale=960:-1',
                        '-q:v', '8',
                        os.path.join(chunk_dir, f'frame_{chunk_num:02d}_%05d.jpg')
                    ]

                    result = subprocess.run(cmd, capture_output=True, timeout=180)
                    if result.returncode != 0:
                        error_msg = result.stderr.decode()[:300] if result.stderr else 'Unknown error'
                        logger.error(f"[EXTRACT] ❌ FFmpeg erro chunk {chunk_num}: {error_msg}")
                        return 0

                    frames = [f for f in os.listdir(chunk_dir) if f.endswith('.jpg')]
                    return len(frames)

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for chunk in range(total_chunks):
                        chunk_start = start + (chunk * 60)
                        remaining = segment_duration - (chunk * 60)
                        chunk_dur = min(60, remaining)

                        future = executor.submit(extract_one_chunk, chunk, chunk_start, chunk_dur)
                        futures[future] = chunk

                    for future in as_completed(futures):
                        chunk_num = futures[future]
                        try:
                            frames_count = future.result()
                            total_frames += frames_count

                            # Atualizar progresso
                            db_local.execute(text("""
                                UPDATE training_videos
                                SET processed_chunks = processed_chunks + 1
                                WHERE id = :video_id
                            """), {'video_id': video_id})
                            db_local.commit()

                            logger.info(f"[EXTRACT] Chunk {chunk_num:02d}/{total_chunks}: {frames_count} frames")

                        except Exception as e:
                            logger.error(f"[EXTRACT] ❌ Chunk {chunk_num} falhou: {e}")

                logger.info(f"[EXTRACT] ✅ Extração completa: {total_frames} frames extraídos")

                # 7. Registrar frames no banco
                logger.info(f"[EXTRACT] Registrando frames no banco...")
                frame_num = 0
                chunk_dirs = sorted([d for d in os.listdir(output_base) if d.startswith('chunk_')])

                for chunk_dir_name in chunk_dirs:
                    chunk_path = os.path.join(output_base, chunk_dir_name)
                    if not os.path.isdir(chunk_path):
                        continue

                    chunk_num = int(chunk_dir_name.replace('chunk_', ''))
                    frame_files = sorted([f for f in os.listdir(chunk_path) if f.endswith('.jpg')])

                    for frame_file in frame_files:
                        frame_path = os.path.join(chunk_path, frame_file)
                        frame_id = str(uuid.uuid4())

                        db_local.execute(text("""
                            INSERT INTO training_frames (id, video_id, frame_number, storage_path, is_annotated, created_at)
                            VALUES (:id, :video_id, :frame_number, :path, FALSE, NOW())
                        """), {
                            'id': frame_id,
                            'video_id': video_id,
                            'frame_number': frame_num,
                            'path': frame_path
                        })

                        frame_num += 1

                        # Commit a cada 100 frames
                        if frame_num % 100 == 0:
                            db_local.commit()
                            logger.info(f"[EXTRACT] Registrados {frame_num}/{total_frames} frames...")

                db_local.commit()
                logger.info(f"[EXTRACT] ✅ {frame_num} frames registrados no banco")

                # 8. Marcar como concluído
                db_local.execute(text("""
                    UPDATE training_videos
                    SET status = 'completed', frame_count = :total
                    WHERE id = :video_id
                """), {'total': frame_num, 'video_id': video_id})
                db_local.commit()

                logger.info(f"[EXTRACT] ========================================")
                logger.info(f"[EXTRACT] ✅ SUCESSO! {frame_num} frames extraídos e registrados")
                logger.info(f"[EXTRACT] ========================================")

            except Exception as e:
                logger.error(f"[EXTRACT] ========================================")
                logger.error(f"[EXTRACT] ❌ ERRO FATAL: {e}")
                logger.error(f"[EXTRACT] Traceback:")
                logger.error(traceback.format_exc())
                logger.error(f"[EXTRACT] ========================================")

                # Marcar como failed
                try:
                    db_local.execute(text("""
                        UPDATE training_videos SET status = 'failed' WHERE id = :video_id
                    """), {'video_id': video_id})
                    db_local.commit()
                    logger.info(f"[EXTRACT] Status atualizado para 'failed'")
                except Exception as db_err:
                    logger.error(f"[EXTRACT] Erro ao atualizar status: {db_err}")

            finally:
                db_local.close()
                logger.info(f"[EXTRACT] Conexão com banco fechada")

        # Start background thread (non-blocking)
        logger.info(f"[UPLOAD] Iniciando thread de extração para {video_id}")
        thread = threading.Thread(
            target=auto_extract_background,
            args=(video_id, storage_path, user_id),  # Pass storage_path, not tmp_path!
            daemon=True
        )
        thread.start()

        return jsonify({
            'success': True,
            'video_id': video_id,
            'message': 'Video uploaded successfully. Frame extraction started in background.'
        })

    except Exception as e:
        logger.error(f"❌ Upload video error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/projects/<project_id>/videos', methods=['GET'])
def list_training_videos(project_id: str):
    """List all videos for a training project."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        from backend.video_db import VideoService
        video_service = VideoService()

        db = get_db_session()
        videos = video_service.list_project_videos(db, project_id, payload['user_id'])

        # Add status information
        videos_with_status = []
        for video in videos:
            video_data = dict(video)
            # Get status from database
            status_row = db.execute(text("""
                SELECT status, processed_chunks, total_chunks, duration_seconds
                FROM training_videos WHERE id = :video_id
            """), {'video_id': video['id']}).fetchone()

            if status_row:
                video_data['status'] = status_row[0]
                video_data['processed_chunks'] = status_row[1] or 0
                video_data['total_chunks'] = status_row[2] or 0
                video_data['duration_seconds'] = status_row[3]

            videos_with_status.append(video_data)

        return jsonify({'success': True, 'videos': videos_with_status})

    except Exception as e:
        logger.error(f"❌ List videos error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/videos/<video_id>', methods=['GET'])
def get_training_video(video_id: str):
    """Get a single training video by ID."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        from backend.video_db import VideoService
        video_service = VideoService()

        db = get_db_session()
        video = video_service.get_video(db, video_id, payload['user_id'])

        if not video:
            return jsonify({'success': False, 'error': 'Video not found'}), 404

        # Add status information
        status_row = db.execute(text("""
            SELECT status, processed_chunks, total_chunks
            FROM training_videos WHERE id = :video_id
        """), {'video_id': video_id}).fetchone()

        if status_row:
            video['status'] = status_row[0]
            video['processed_chunks'] = status_row[1] or 0
            video['total_chunks'] = status_row[2] or 0

        return jsonify({'success': True, 'video': video})

    except Exception as e:
        logger.error(f"❌ Get video error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/videos/<video_id>/extract', methods=['POST'])
def extract_video_frames(video_id: str):
    """
    Manually start frame extraction for a video.

    This endpoint is for re-extraction or manual extraction.
    Normally extraction starts automatically after upload.
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        user_id = payload['user_id']
        db = get_db_session()

        # Check video ownership and current status
        video_row = db.execute(text("""
            SELECT status FROM training_videos v
            JOIN training_projects p ON p.id = v.project_id
            WHERE v.id = :video_id AND p.user_id = :user_id
            FOR UPDATE
        """), {'video_id': video_id, 'user_id': user_id}).fetchone()

        if not video_row:
            return jsonify({'success': False, 'error': 'Video not found'}), 404

        current_status = video_row[0]
        if current_status == 'extracting':
            return jsonify({
                'success': False,
                'error': 'Video is already extracting',
                'status': current_status
            }), 400

        if current_status == 'completed':
            return jsonify({
                'success': False,
                'error': 'Video has already been extracted',
                'status': current_status
            }), 400

        # Mark as extracting
        db.execute(text("""
            UPDATE training_videos SET status = 'extracting' WHERE id = :video_id
        """), {'video_id': video_id})
        db.commit()

        # Start extraction in background
        def extract_background(video_id, user_id):
            try:
                db_local = next(get_db())
                processor = VideoProcessor()
                result = processor.extract_frames(
                    db=db_local,
                    video_id=video_id,
                    user_id=user_id
                )

                if result.get('success'):
                    logger.info(f"✅ Manual extraction complete: {video_id}")
                else:
                    logger.error(f"❌ Manual extraction failed: {video_id}")
            except Exception as e:
                logger.error(f"❌ Manual extraction error: {e}")
            finally:
                db_local.close()

        thread = threading.Thread(
            target=extract_background,
            args=(video_id, user_id),
            daemon=True
        )
        thread.start()

        return jsonify({
            'success': True,
            'message': 'Frame extraction started'
        })

    except Exception as e:
        logger.error(f"❌ Extract frames error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/videos/<video_id>/frames', methods=['GET'])
def list_video_frames(video_id: str):
    """List all frames extracted from a video."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        db = get_db_session()
        query = text("""
            SELECT id, frame_number, storage_path,
                   is_annotated, created_at
            FROM training_frames
            WHERE video_id = :video_id
            ORDER BY frame_number ASC
        """)

        result = db.execute(query, {'video_id': video_id})
        rows = result.fetchall()

        frames = [
            {
                'id': str(row[0]),
                'frame_number': row[1],
                'storage_path': row[2],
                'is_annotated': row[3],
                'created_at': row[4].isoformat() if row[4] else None,
                'image_url': f"/api/training/frames/{str(row[0])}/image"
            }
            for row in rows
        ]

        return jsonify({'success': True, 'frames': frames})

    except Exception as e:
        logger.error(f"❌ List frames error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/frames/<frame_id>/image', methods=['GET'])
def serve_frame_image(frame_id: str):
    """Serve frame image file."""
    try:
        db = get_db_session()
        query = text("""
            SELECT storage_path FROM training_frames WHERE id = :frame_id
        """)
        result = db.execute(query, {'frame_id': frame_id})
        row = result.fetchone()

        if not row:
            return jsonify({'success': False, 'error': 'Frame not found'}), 404

        frame_path = row[0]

        if not os.path.exists(frame_path):
            logger.error(f"❌ Frame image file not found: {frame_path}")
            return jsonify({'success': False, 'error': 'Frame image file not found on disk'}), 404

        return send_from_directory(os.path.dirname(frame_path), os.path.basename(frame_path))

    except Exception as e:
        logger.error(f"❌ Serve frame image error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/frames/<frame_id>/annotations', methods=['GET'])
def get_frame_annotations(frame_id: str):
    """Get annotations for a specific frame."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        db = get_db_session()
        query = text("""
            SELECT id, class_id, bbox_x, bbox_y, bbox_width, bbox_height, created_at
            FROM frame_annotations
            WHERE frame_id = :frame_id
            ORDER BY created_at ASC
        """)

        result = db.execute(query, {'frame_id': frame_id})
        rows = result.fetchall()

        annotations = [
            {
                'id': str(row[0]),
                'class_id': row[1],
                'x_center': float(row[2]),
                'y_center': float(row[3]),
                'width': float(row[4]),
                'height': float(row[5]),
                'created_at': row[6].isoformat() if row[6] else None
            }
            for row in rows
        ]

        return jsonify({'success': True, 'annotations': annotations})

    except Exception as e:
        logger.error(f"❌ Get annotations error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/frames/<frame_id>/annotations', methods=['POST'])
def save_frame_annotations(frame_id: str):
    """Save annotations for a specific frame."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        data = request.get_json()
        annotations = data.get('annotations', [])

        db = get_db_session()

        # Delete existing annotations
        db.execute(text("""
            DELETE FROM frame_annotations WHERE frame_id = :frame_id
        """), {'frame_id': frame_id})

        # Se não tem annotations, marcar como não anotado
        if len(annotations) == 0:
            db.execute(text("""
                UPDATE training_frames
                SET is_annotated = FALSE
                WHERE id = :frame_id
            """), {'frame_id': frame_id})
            db.commit()
            return jsonify({'success': True, 'saved': 0})

        # Insert new annotations
        for ann in annotations:
            annotation_id = str(uuid.uuid4())
            db.execute(text("""
                INSERT INTO frame_annotations (id, frame_id, class_id, bbox_x, bbox_y, bbox_width, bbox_height, created_by, created_at)
                VALUES (:id, :frame_id, :class_id, :bbox_x, :bbox_y, :bbox_width, :bbox_height, :created_by, NOW())
            """), {
                'id': annotation_id,
                'frame_id': frame_id,
                'class_id': ann.get('class_id'),
                'bbox_x': ann.get('x_center'),
                'bbox_y': ann.get('y_center'),
                'bbox_width': ann.get('width'),
                'bbox_height': ann.get('height'),
                'created_by': payload['user_id']
            })

        # Update frame annotation status
        db.execute(text("""
            UPDATE training_frames
            SET is_annotated = TRUE
            WHERE id = :frame_id
        """), {'frame_id': frame_id})

        db.commit()

        return jsonify({'success': True, 'saved': len(annotations)})

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Save annotations error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# YOLO Classes API
# ============================================================================

@app.route('/api/classes', methods=['GET'])
def list_classes():
    """Lista classes YOLO para anotação"""
    db = get_db_session()

    # Criar tabela yolo_classes se não existir
    try:
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS yolo_classes (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL UNIQUE,
                color VARCHAR(7) NOT NULL DEFAULT '#22c55e',
                created_at TIMESTAMP DEFAULT NOW()
            )
        """))
        db.commit()
    except Exception as e:
        logger.warning(f"Tabela yolo_classes pode já existir: {e}")

    result = db.execute(text(
        "SELECT id, name, color FROM yolo_classes ORDER BY id"
    )).fetchall()

    # Se vazio, inserir defaults
    if len(result) == 0:
        defaults = [
            ('Produto', '#22c55e'), ('Caminhão', '#f59e0b'),
            ('Placa', '#3b82f6'), ('Capacete', '#8b5cf6'),
            ('Colete', '#ec4899'), ('Sem EPI', '#ef4444'),
        ]
        for name, color in defaults:
            db.execute(text(
                "INSERT INTO yolo_classes (name, color) VALUES (:name, :color)"
            ), {"name": name, "color": color})
        db.commit()
        result = db.execute(text(
            "SELECT id, name, color FROM yolo_classes ORDER BY id"
        )).fetchall()

    classes = [{"id": r[0], "name": r[1], "color": r[2]} for r in result]
    return jsonify({"success": True, "classes": classes})


@app.route('/api/classes', methods=['POST'])
def create_class():
    """Cria nova classe YOLO"""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"success": False, "error": "Missing token"}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({"success": False, "error": "Invalid token"}), 401

        data = request.get_json()
        name = data.get('name', '').strip()
        color = data.get('color', '#22c55e')

        if not name:
            return jsonify({"success": False, "error": "Nome obrigatório"}), 400

        db = get_db_session()
        db.execute(text(
            "INSERT INTO yolo_classes (name, color) VALUES (:name, :color)"
        ), {"name": name, "color": color})
        db.commit()

        row = db.execute(text(
            "SELECT id, name, color FROM yolo_classes WHERE name = :name"
        ), {"name": name}).fetchone()

        return jsonify({
            "success": True,
            "class": {"id": row[0], "name": row[1], "color": row[2]}
        })
    except Exception as e:
        if "unique" in str(e).lower() or "duplicate" in str(e).lower():
            return jsonify({"success": False, "error": "Classe já existe"}), 409
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/training/frames/<frame_id>/predict', methods=['POST'])
def predict_frame(frame_id):
    """Roda YOLO no frame para pré-detectar objetos"""
    try:
        db = get_db_session()
        frame = db.execute(text(
            "SELECT storage_path FROM training_frames WHERE id = :id"
        ), {"id": frame_id}).fetchone()

        if not frame:
            return jsonify({"success": False, "error": "Frame not found"}), 404

        image_path = frame[0]
        if not os.path.exists(image_path):
            return jsonify({"success": True, "annotations": [],
                          "message": "Frame file not found on disk"}), 200

        # Tentar rodar YOLO se disponível
        try:
            from ultralytics import YOLO

            # Tentar usar modelo customizado, se não existir usar o base
            model_path = "models/best.pt"
            if not os.path.exists(model_path):
                model_path = "models/yolov8n.pt"

            if os.path.exists(model_path):
                model = YOLO(model_path)
                results = model(image_path)
                annotations = []
                for r in results:
                    for box in r.boxes:
                        annotations.append({
                            "class_id": int(box.cls),
                            "x_center": float(box.xywhn[0][0]),
                            "y_center": float(box.xywhn[0][1]),
                            "width": float(box.xywhn[0][2]),
                            "height": float(box.xywhn[0][3]),
                            "confidence": float(box.conf),
                        })
                return jsonify({"success": True, "annotations": annotations})
            else:
                return jsonify({"success": True, "annotations": [],
                              "message": "No model available yet"})
        except ImportError:
            return jsonify({"success": True, "annotations": [],
                          "message": "YOLO not installed"})
    except Exception as e:
        logger.error(f"❌ Predict error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# ============================================================================
# Training API Aliases (Simplified Routes without project_id)
# ============================================================================

@app.route('/api/training/videos', methods=['GET'])
def list_all_videos():
    """
    List all training videos for the current user.
    Simplified route that doesn't require project_id.
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        user_id = payload['user_id']
        db = get_db_session()

        # Get user's default project (or first project)
        project = db.execute(text("""
            SELECT id FROM training_projects
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 1
        """), {'user_id': user_id}).fetchone()

        if not project:
            # No project exists, return empty list
            return jsonify({'success': True, 'videos': []})

        project_id = str(project[0])

        # Use existing endpoint logic
        from backend.video_db import VideoService
        video_service = VideoService()
        videos = video_service.list_project_videos(db, project_id, user_id)

        # Add status information
        videos_with_status = []
        for video in videos:
            video_data = dict(video)
            status_row = db.execute(text("""
                SELECT status, processed_chunks, total_chunks, duration_seconds
                FROM training_videos WHERE id = :video_id
            """), {'video_id': video['id']}).fetchone()

            if status_row:
                video_data['status'] = status_row[0]
                video_data['processed_chunks'] = status_row[1] or 0
                video_data['total_chunks'] = status_row[2] or 0
                video_data['duration_seconds'] = status_row[3]

            videos_with_status.append(video_data)

        return jsonify({'success': True, 'videos': videos_with_status})

    except Exception as e:
        logger.error(f"❌ List all videos error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/videos/upload', methods=['POST'])
def upload_video_alias():
    """
    Upload a training video without requiring project_id.
    Creates or uses user's default project.
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        user_id = payload['user_id']
        db = get_db_session()

        # Get or create default project
        project = db.execute(text("""
            SELECT id FROM training_projects
            WHERE user_id = :user_id
            ORDER BY created_at DESC
            LIMIT 1
        """), {'user_id': user_id}).fetchone()

        if not project:
            # Create default project
            from backend.training_db import TrainingProjectDB
            project_db = TrainingProjectDB()
            project = project_db.create_project(
                db=db,
                user_id=user_id,
                name='Default Project',
                description='Automatically created project'
            )
            if not project:
                return jsonify({'success': False, 'error': 'Failed to create project'}), 500
            project_id = project['id']
        else:
            project_id = str(project[0])

        # Delegate to existing endpoint
        return upload_training_video(project_id)

    except Exception as e:
        logger.error(f"❌ Upload video alias error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/videos/<video_id>', methods=['DELETE'])
def delete_video_alias(video_id: str):
    """
    Delete a training video.
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        user_id = payload['user_id']
        db = get_db_session()

        # Verify ownership
        check = db.execute(text("""
            SELECT v.id FROM training_videos v
            JOIN training_projects p ON p.id = v.project_id
            WHERE v.id = :video_id AND p.user_id = :user_id
        """), {'video_id': video_id, 'user_id': user_id}).fetchone()

        if not check:
            return jsonify({'success': False, 'error': 'Video not found'}), 404

        # Delete frames and annotations (cascade)
        db.execute(text("""
            DELETE FROM frame_annotations WHERE frame_id IN (
                SELECT id FROM training_frames WHERE video_id = :video_id
            )
        """), {'video_id': video_id})

        db.execute(text("""
            DELETE FROM training_frames WHERE video_id = :video_id
        """), {'video_id': video_id})

        db.execute(text("""
            DELETE FROM training_videos WHERE id = :video_id
        """), {'video_id': video_id})

        db.commit()

        logger.info(f"✅ Video deleted: {video_id}")

        return jsonify({'success': True, 'message': 'Video deleted'})

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Delete video error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/videos/<video_id>', methods=['PATCH'])
def update_video(video_id: str):
    """
    Update a training video (e.g., rename).
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        user_id = payload['user_id']
        data = request.get_json()
        name = data.get('name')

        if not name:
            return jsonify({'success': False, 'error': 'name is required'}), 400

        db = get_db_session()

        # Verify ownership
        check = db.execute(text("""
            SELECT v.id FROM training_videos v
            JOIN training_projects p ON p.id = v.project_id
            WHERE v.id = :video_id AND p.user_id = :user_id
        """), {'video_id': video_id, 'user_id': user_id}).fetchone()

        if not check:
            return jsonify({'success': False, 'error': 'Video not found'}), 404

        # Update name
        db.execute(text("""
            UPDATE training_videos SET name = :name WHERE id = :video_id
        """), {'name': name, 'video_id': video_id})

        db.commit()

        logger.info(f"✅ Video renamed: {video_id} -> {name}")

        return jsonify({'success': True, 'message': 'Video updated'})

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Update video error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Application Entry Point
# ============================================================================

# Initialize database tables on startup
def init_database_tables():
    """Create necessary tables if they don't exist"""
    try:
        db = get_db_session()
        try:
            # Create frame_annotations table
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS frame_annotations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    frame_id UUID NOT NULL,
                    class_id INTEGER NOT NULL,
                    bbox_x FLOAT NOT NULL,
                    bbox_y FLOAT NOT NULL,
                    bbox_width FLOAT NOT NULL,
                    bbox_height FLOAT NOT NULL,
                    created_by UUID NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW(),

                    CONSTRAINT fk_frame_annotations_frame
                        FOREIGN KEY (frame_id)
                        REFERENCES training_frames(id)
                        ON DELETE CASCADE,

                    CONSTRAINT fk_frame_annotations_user
                        FOREIGN KEY (created_by)
                        REFERENCES users(id)
                        ON DELETE CASCADE
                )
            """))
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_frame_annotations_frame_id ON frame_annotations(frame_id)
            """))
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_frame_annotations_class_id ON frame_annotations(class_id)
            """))
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_frame_annotations_created_by ON frame_annotations(created_by)
            """))
            db.commit()
            logger.info("✅ Tabela frame_annotations verificada/criada")
        except Exception as e:
            logger.warning(f"Erro ao criar frame_annotations: {e}")
            db.rollback()
        finally:
            # Connection fechada automaticamente pelo teardown
            pass
    except Exception as e:
        logger.error(f"❌ Erro na inicialização do banco: {e}")


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Starting EPI Recognition System API Server")

    # Initialize database tables
    init_database_tables()

    logger.info("=" * 60)
    logger.info("=" * 60)
    logger.info(f"📡 WebSocket support: ENABLED")
    logger.info(f"📹 HLS streaming: ENABLED")
    logger.info(f"🎯 YOLO detection: ENABLED")
    logger.info(f"🌐 Server running on: http://0.0.0.0:{PORT}")
    # logger.info(f"🔌 WebSocket endpoint: ws://localhost:{PORT}/socket.io/")  # TODO: Implement WebSocket
    logger.info("=" * 60)

    # Run with SocketIO if available, otherwise use regular Flask
    if socketio:
        socketio.run(
            app,
            host='0.0.0.0',
            port=PORT,
            debug=True,
            allow_unsafe_werkzeug=True
        )
    else:
        app.run(
            host='0.0.0.0',
            port=PORT,
            debug=True
        )
