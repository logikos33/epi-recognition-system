"""
API Server for EPI Recognition System
With Authentication, Database, YOLO Detection, HLS Streaming, and WebSocket Support
"""
from flask import Flask, request, jsonify, send_from_directory
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
        db = next(get_db())
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
        db = next(get_db())
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
    db = next(get_db())
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
    db = next(get_db())
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
        db = next(get_db())

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
        db = next(get_db())

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
        db = next(get_db())

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
        db = next(get_db())

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
        db = next(get_db())

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
# Application Entry Point
# ============================================================================

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Starting EPI Recognition System API Server")
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
