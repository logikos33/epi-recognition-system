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
import json
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
import traceback
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Add backend directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

# Import database modules
from backend.database import get_db, get_db_context, init_db, SessionLocal
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
from training.training_optimizer import TrainingResourceManager

# Configure logging
os.makedirs('logs', exist_ok=True)

# Configurar logging persistente
if not logging.getLogger().handlers:
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        handlers=[
            logging.FileHandler('logs/api_server.log'),
            logging.StreamHandler(sys.stdout)
        ],
        force=False  # Não sobrescrever handlers existentes
    )
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=os.environ.get('CORS_ORIGINS', '*').split(','))

# ============================================================================
# Camera System Blueprint (Feature 1)
# ============================================================================
from cameras.routes import cameras_bp
app.register_blueprint(cameras_bp, url_prefix='/api/cameras')

# Iniciar health checker de câmeras (background thread)
from cameras.health_checker import CameraHealthChecker
camera_health_checker = CameraHealthChecker()
camera_health_checker.start()

# ============================================================================
# Rules Engine Blueprint (FASE 3 - State Machine para processamento YOLO)
# ============================================================================
from rules.routes import rules_bp, sessions_bp
app.register_blueprint(rules_bp, url_prefix='/api/rules')
app.register_blueprint(sessions_bp, url_prefix='/api/sessions')

# ============================================================================
# Dashboard Blueprint (FASE 5 - KPIs e Excel Export)
# ============================================================================
from dashboard.routes import dashboard_bp
app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')


# ============================================================================
# Global Exception Handlers - Backend Never Crashes
# ============================================================================

# Handler global para exceções não tratadas - backend retorna JSON, nunca crasha
@app.errorhandler(Exception)
def handle_unhandled_exception(e):
    """
    Captura TODAS as exceções não tratadas no Flask.
    Backend sempre retorna JSON com erro, nunca cai.
    """
    logger.error(
        f"[UNHANDLED] {request.method} {request.path} → "
        f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"
    )
    return jsonify({
        'error': 'Erro interno do servidor',
        'type': type(e).__name__,
        'timestamp': datetime.datetime.now().isoformat()
    }), 500


@app.errorhandler(404)
def handle_not_found(e):
    """Endpoint não encontrado - retorna JSON amigável."""
    return jsonify({'error': 'Endpoint não encontrado', 'path': request.path}), 404


@app.errorhandler(405)
def handle_method_not_allowed(e):
    """Método HTTP não permitido - retorna JSON amigável."""
    return jsonify({'error': 'Método não permitido', 'path': request.path}), 405


# Capturar exceções em threads de background (treinamento, health checker, etc.)
def handle_thread_exception(args):
    """
    Captura crashes em threads de background.
    Thread crasha mas o processo principal continua vivo.
    """
    logger.error(
        f"[THREAD CRASH] Thread '{args.thread.name}': "
        f"{args.exc_type.__name__}: {args.exc_value}\n"
        f"{''.join(traceback.format_tb(args.exc_traceback))}"
    )


threading.excepthook = handle_thread_exception


def _backend_heartbeat():
    """Loga a cada 60s que o backend está vivo. Útil para diagnóstico."""
    import time as _time
    while True:
        logger.info(
            f"[HEARTBEAT] Backend vivo | "
            f"threads={threading.active_count()}"
        )
        _time.sleep(60)

_hb = threading.Thread(target=_backend_heartbeat, daemon=True, name="heartbeat")
_hb.start()


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

# Detection callback for WebSocket broadcasting + Rules Engine processing
def on_detection_result(result: dict):
    """Callback for YOLO detection results - processes via Rules Engine + broadcasts via WebSocket"""
    try:
        camera_id = result.get('camera_id')
        detections = result.get('detections', [])

        # NOVO: Processar detecções através da Rules Engine
        if camera_id and detections:
            try:
                from rules.service import get_rules_engine
                rules_engine = get_rules_engine()
                actions = rules_engine.process_detections(str(camera_id), detections)

                # Logar ações executadas
                for action in actions:
                    logger.info(f"✅ Rules action: {action.get('action_type')} for camera {camera_id}")
            except Exception as rules_error:
                logger.error(f"❌ Rules Engine error: {rules_error}")

        # Emit to camera-specific room (mantido)
        room = f"camera_{result['camera_id']}"
        socketio.emit('detection', result, room=room)
        logger.debug(f"📡 Emitted detection to {room}: {len(result.get('detections', []))} objects")
    except Exception as e:
        logger.error(f"❌ Error in detection callback: {e}")

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


@app.after_request
def add_security_headers(response):
    """Headers de segurança HTTP para produção."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    if os.environ.get('FLASK_ENV') == 'production':
        response.headers['Strict-Transport-Security'] = \
            'max-age=31536000; includeSubDomains'
    return response


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
            'role': user.get('role', 'operator'),
            'exp': datetime.datetime.now(datetime.timezone.utc) + timedelta(days=7)
        }, SECRET_KEY, algorithm='HS256')

        logger.info(f"✅ User logged in: {email} (role: {user.get('role', 'operator')})")

        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user.get('full_name'),
                'company_name': user.get('company_name'),
                'role': user.get('role', 'operator')
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
    """Get status of all active streams and detections.
    NOTE: Public endpoint - no auth required for health monitoring."""
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
    NOTE: Public endpoint - no auth required for health monitoring.
    """
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

    Request body (optional):
    {
        "start_time": 120,  # Start time in seconds (optional)
        "end_time": 480     # End time in seconds (optional)
    }

    If start_time and end_time are provided, extracts only that segment.
    Otherwise, extracts the full video.
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

        # Get optional time range parameters
        data = request.get_json() or {}
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        # Validate time range parameters
        if start_time is not None and end_time is not None:
            if not isinstance(start_time, (int, float)) or not isinstance(end_time, (int, float)):
                return jsonify({'success': False, 'error': 'start_time and end_time must be numbers'}), 400

            if start_time < 0 or end_time < 0:
                return jsonify({'success': False, 'error': 'start_time and end_time must be non-negative'}), 400

            if start_time >= end_time:
                return jsonify({'success': False, 'error': 'start_time must be less than end_time'}), 400

            segment_duration = end_time - start_time
            if segment_duration < 60:
                return jsonify({'success': False, 'error': f'Segment duration too short: {segment_duration}s (minimum: 60s)'}), 400

        elif start_time is not None or end_time is not None:
            # Only one provided
            return jsonify({'success': False, 'error': 'Both start_time and end_time must be provided together'}), 400

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
        def extract_background(video_id, user_id, start_time, end_time):
            try:
                with get_db_context() as db_local:
                    processor = VideoProcessor()
                    result = processor.extract_frames(
                        db=db_local,
                        video_id=video_id,
                        user_id=user_id,
                        start_time=start_time,
                        end_time=end_time
                    )

                    if result.get('success'):
                        logger.info(f"✅ Manual extraction complete: {video_id}")
                    else:
                        logger.error(f"❌ Manual extraction failed: {video_id}")
            except Exception as e:
                logger.error(f"❌ Manual extraction error: {e}")

        thread = threading.Thread(
            target=extract_background,
            args=(video_id, user_id, start_time, end_time),
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
    """Serve frame image file.

    GET /api/training/frames/{frame_id}/image
    Returns JPEG image from training frame.
    """
    # Validar formato do UUID antes de consultar o banco
    import re
    uuid_pattern = re.compile(
        r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$',
        re.IGNORECASE
    )

    if not uuid_pattern.match(frame_id):
        logger.warning(f"Invalid UUID format: {frame_id}")
        return jsonify({
            'success': False,
            'error': 'Invalid frame ID format',
            'details': 'Frame ID must be a valid UUID'
        }), 400

    try:
        db = get_db_session()
        query = text("""
            SELECT storage_path FROM training_frames WHERE id = :frame_id
        """)
        result = db.execute(query, {'frame_id': frame_id})
        row = result.fetchone()

        if not row:
            logger.warning(f"Frame not found in database: {frame_id}")
            return jsonify({
                'success': False,
                'error': 'Frame not found'
            }), 404

        frame_path = row[0]

        if not os.path.exists(frame_path):
            logger.error(f"❌ Frame image file not found: {frame_path} (id={frame_id})")
            return jsonify({
                'success': False,
                'error': 'Frame image file not found on disk'
            }), 404

        # Serve imagem com cache de 5 minutos
        from flask import send_file
        return send_file(
            frame_path,
            mimetype='image/jpeg',
            max_age=300
        )

    except Exception as e:
        logger.error(f"❌ Serve frame image error for {frame_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


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
# Training Images API (Direct Image Upload)
# ============================================================================

@app.route('/api/training/images/upload', methods=['POST'])
def upload_training_images():
    """
    Upload one or more training images directly (without video).

    Images can be annotated like frames extracted from videos.
    Supports JPG, PNG formats (max 10MB per image).
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

        # Check if files are present
        if 'images' not in request.files:
            return jsonify({'success': False, 'error': 'No files provided'}), 400

        files = request.files.getlist('images')
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'error': 'No files selected'}), 400

        # Validate file count
        if len(files) > 100:
            return jsonify({'success': False, 'error': 'Maximum 100 images per upload'}), 400

        # Create storage directory
        storage_dir = 'storage/training_images'
        os.makedirs(storage_dir, exist_ok=True)

        uploaded_images = []

        with get_db_context() as db:
            for file in files:
                # Validate file extension
                filename = secure_filename(file.filename)
                if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                    logger.warning(f"Skipping invalid file: {filename}")
                    continue

                # Validate file size (10MB max)
                file.seek(0, os.SEEK_END)
                file_size = file.tell()
                file.seek(0)

                if file_size > 10 * 1024 * 1024:  # 10MB
                    logger.warning(f"Skipping oversized file: {filename} ({file_size} bytes)")
                    continue

                # Generate unique filename
                image_id = str(uuid.uuid4())
                ext = os.path.splitext(filename)[1]
                saved_filename = f"{image_id}{ext}"
                save_path = os.path.join(storage_dir, saved_filename)

                # Save file
                file.save(save_path)

                # Insert into database
                db.execute(text("""
                    INSERT INTO imagens_treinamento
                    (caminho, conjunto, validada)
                    VALUES (:caminho, 'train', false)
                    RETURNING id
                """), {
                    'caminho': save_path
                })

                row = db.execute(text("SELECT lastval()")).fetchone()
                db_id = row[0]

                uploaded_images.append({
                    'id': str(db_id),
                    'filename': saved_filename,
                    'original_name': filename,
                    'size': file_size,
                    'path': save_path
                })

        return jsonify({
            'success': True,
            'uploaded_count': len(uploaded_images),
            'images': uploaded_images
        })

    except Exception as e:
        logger.error(f"❌ Upload training images error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/images', methods=['GET'])
def list_training_images():
    """List all uploaded training images for the current user."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        with get_db_context() as db:
            result = db.execute(text("""
                SELECT id, caminho, validada, conjunto, criado_em
                FROM imagens_treinamento
                ORDER BY criado_em DESC
                LIMIT 500
            """))

            rows = result.fetchall()

            images = []
            for row in rows:
                # Check if file exists
                file_path = row[1]
                exists = os.path.exists(file_path)

                images.append({
                    'id': str(row[0]),
                    'path': file_path,
                    'is_validated': row[2],
                    'split': row[3],
                    'created_at': row[4].isoformat() if row[4] else None,
                    'exists': exists,
                    'image_url': f"/api/training/images/{str(row[0])}/image" if exists else None
                })

            return jsonify({
                'success': True,
                'count': len(images),
                'images': images
            })

    except Exception as e:
        logger.error(f"❌ List training images error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/images/<int:image_id>', methods=['DELETE'])
def delete_training_image(image_id: int):
    """Delete a training image and its file."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        with get_db_context() as db:
            # Get image path
            result = db.execute(text("""
                SELECT caminho FROM imagens_treinamento
                WHERE id = :image_id
            """), {'image_id': image_id})

            row = result.fetchone()

            if not row:
                return jsonify({'success': False, 'error': 'Image not found'}), 404

            file_path = row[0]

            # Delete from database
            db.execute(text("""
                DELETE FROM imagens_treinamento
                WHERE id = :image_id
            """), {'image_id': image_id})

            # Delete file from disk
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                    logger.info(f"✅ Deleted image file: {file_path}")
                except Exception as e:
                    logger.warning(f"⚠️  Could not delete file: {e}")

            return jsonify({'success': True, 'message': 'Image deleted'})

    except Exception as e:
        logger.error(f"❌ Delete training image error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/images/<int:image_id>/image', methods=['GET'])
def serve_training_image(image_id: int):
    """Serve a training image file."""
    try:
        with get_db_context() as db:
            result = db.execute(text("""
                SELECT caminho FROM imagens_treinamento
                WHERE id = :image_id
            """), {'image_id': image_id})

            row = result.fetchone()

            if not row:
                return jsonify({'success': False, 'error': 'Image not found'}), 404

            image_path = row[0]

            if not os.path.exists(image_path):
                logger.error(f"❌ Training image file not found: {image_path}")
                return jsonify({'success': False, 'error': 'Image file not found on disk'}), 404

            return send_from_directory(
                os.path.dirname(image_path),
                os.path.basename(image_path)
            )

    except Exception as e:
        logger.error(f"❌ Serve training image error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Training Control API
# ============================================================================

# Global tracking for active training subprocesses
active_training_processes = {}  # job_id -> subprocess.Popen


def init_training_tables():
    """Initialize training_jobs and trained_models tables if they don't exist."""
    try:
        with get_db_context() as db:
            # Create training_jobs table
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS training_jobs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    name VARCHAR(255) NOT NULL,
                    status VARCHAR(20) DEFAULT 'pending',
                    preset VARCHAR(20) NOT NULL,
                    model_size VARCHAR(10) NOT NULL,
                    epochs INTEGER NOT NULL,
                    dataset_yaml_path VARCHAR(500),
                    model_output_path VARCHAR(500),
                    progress INTEGER DEFAULT 0,
                    current_epoch INTEGER DEFAULT 0,
                    metrics JSONB,
                    error_message TEXT,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))

            # Create trained_models table
            db.execute(text("""
                CREATE TABLE IF NOT EXISTS trained_models (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    job_id UUID REFERENCES training_jobs(id) ON DELETE SET NULL,
                    name VARCHAR(255) NOT NULL,
                    model_path VARCHAR(500) NOT NULL,
                    model_size VARCHAR(10) NOT NULL,
                    is_active BOOLEAN DEFAULT FALSE,
                    metrics JSONB,
                    created_at TIMESTAMP DEFAULT NOW()
                )
            """))

            # Create indexes
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_training_jobs_user_id ON training_jobs(user_id)
            """))
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_training_jobs_status ON training_jobs(status)
            """))
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_training_jobs_created_at ON training_jobs(created_at DESC)
            """))
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_trained_models_user_id ON trained_models(user_id)
            """))
            db.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_trained_models_is_active ON trained_models(is_active)
                WHERE is_active = TRUE
            """))
            db.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_trained_models_user_active
                ON trained_models(user_id) WHERE is_active = TRUE
            """))

        logger.info("✅ Training tables initialized")
        return True
    except Exception as e:
        logger.error(f"❌ Failed to initialize training tables: {e}")
        return False


@app.route('/api/training/dataset/stats', methods=['GET'])
def get_dataset_stats():
    """
    Get dataset statistics for training.

    Returns:
    - Total annotated frames
    - Total bounding boxes
    - Class distribution
    - Train/val split info

    Note: Admins see all data, operators see only their own data.
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

        with get_db_context() as db:
            # Check if user is admin
            user = db.execute(text("SELECT role FROM users WHERE id = :user_id"), {'user_id': user_id}).fetchone()
            user_role = user[0] if user else 'operator'

            # Build WHERE clause based on role
            # Admin: no filter (see all data)
            # Operator: filter by user_id
            if user_role == 'admin':
                where_clause = ""
                params = {}
            else:
                where_clause = "WHERE tv.user_id = :user_id"
                params = {'user_id': user_id}

            # Get total annotated frames
            result = db.execute(text(f"""
                SELECT COUNT(DISTINCT fa.frame_id)
                FROM frame_annotations fa
                JOIN training_frames tf ON tf.id = fa.frame_id
                JOIN training_videos tv ON tv.id = tf.video_id
                {where_clause}
            """), params)
            total_frames = result.scalar() or 0

            # Get total bounding boxes
            result = db.execute(text(f"""
                SELECT COUNT(*)
                FROM frame_annotations fa
                JOIN training_frames tf ON tf.id = fa.frame_id
                JOIN training_videos tv ON tv.id = tf.video_id
                {where_clause}
            """), params)
            total_boxes = result.scalar() or 0

            # Get class distribution
            result = db.execute(text(f"""
                SELECT yc.name, COUNT(*) as count
                FROM frame_annotations fa
                JOIN training_frames tf ON tf.id = fa.frame_id
                JOIN training_videos tv ON tv.id = tf.video_id
                JOIN yolo_classes yc ON yc.id = fa.class_id
                {where_clause}
                GROUP BY yc.name
                ORDER BY count DESC
            """), params)
            class_distribution = {row[0]: row[1] for row in result}

            return jsonify({
                'success': True,
                'stats': {
                    'total_frames': total_frames,
                    'total_boxes': total_boxes,
                    'class_distribution': class_distribution,
                    'train_split': int(total_frames * 0.8),
                    'val_split': int(total_frames * 0.2)
                }
            })

    except Exception as e:
        logger.error(f"❌ Get dataset stats error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/dataset/export', methods=['POST'])
def export_dataset():
    """
    Export dataset in YOLO format.

    Creates:
    - images/train/, images/val/
    - labels/train/, labels/val/
    - data.yaml

    Returns path to exported dataset.
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

        # Initialize tables if needed
        init_training_tables()

        from datetime import datetime

        # Create dataset directory with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dataset_base = 'storage/datasets'
        dataset_path = os.path.join(dataset_base, timestamp)

        images_train = os.path.join(dataset_path, 'images', 'train')
        images_val = os.path.join(dataset_path, 'images', 'val')
        labels_train = os.path.join(dataset_path, 'labels', 'train')
        labels_val = os.path.join(dataset_path, 'labels', 'val')

        for dir_path in [images_train, images_val, labels_train, labels_val]:
            os.makedirs(dir_path, exist_ok=True)

        with get_db_context() as db:
            # Get all annotated frames with splits
            result = db.execute(text("""
                SELECT
                    tf.id as frame_id,
                    tf.storage_path as image_path,
                    ROW_NUMBER() OVER (ORDER BY tf.id) as row_num
                FROM training_frames tf
                JOIN training_videos tv ON tv.id = tf.video_id
                JOIN training_projects tp ON tp.id = tv.project_id
                WHERE tp.user_id = :user_id
                AND EXISTS (
                    SELECT 1 FROM frame_annotations fa
                    WHERE fa.frame_id = tf.id
                )
                ORDER BY tf.id
            """), {'user_id': user_id})

            frames = result.fetchall()

            if not frames:
                return jsonify({'success': False, 'error': 'No annotated frames found'}), 400

            total_frames = len(frames)
            train_count = int(total_frames * 0.8)

            # CRITICAL FIX: Get YOLO classes and create ID mapping BEFORE export
            # YOLO requires 0-based sequential indices (0, 1, 2...)
            # Database has arbitrary IDs (possibly starting from 1, 2, 5, etc.)
            classes_result = db.execute(text("""
                SELECT id, name FROM yolo_classes ORDER BY id ASC
            """))
            classes = classes_result.fetchall()

            # Create mapping: database_id -> yolo_index (0, 1, 2...)
            class_id_to_yolo_index = {}
            yolo_index_to_class_info = {}  # For data.yaml
            for yolo_index, (db_id, class_name) in enumerate(classes):
                class_id_to_yolo_index[db_id] = yolo_index
                yolo_index_to_class_info[yolo_index] = class_name

            num_classes = len(classes)
            logger.info(f"✅ Class mapping: {len(class_id_to_yolo_index)} classes → YOLO indices 0-{num_classes-1}")

            # Copy frames and export annotations
            for frame in frames:
                frame_id = str(frame[0])
                image_path = frame[1]
                row_num = frame[2]

                # Determine split
                is_train = row_num <= train_count
                split_name = 'train' if is_train else 'val'

                # Copy image
                if os.path.exists(image_path):
                    image_filename = f"{frame_id}.jpg"
                    dest_image = os.path.join(
                        images_train if is_train else images_val,
                        image_filename
                    )
                    shutil.copy(image_path, dest_image)

                # Export annotations
                annotations_result = db.execute(text("""
                    SELECT
                        yc.id as class_id,
                        fa.bbox_x,
                        fa.bbox_y,
                        fa.bbox_width,
                        fa.bbox_height
                    FROM frame_annotations fa
                    JOIN yolo_classes yc ON yc.id = fa.class_id
                    WHERE fa.frame_id = :frame_id
                """), {'frame_id': frame_id})

                annotations = annotations_result.fetchall()

                label_filename = f"{frame_id}.txt"
                label_path = os.path.join(
                    labels_train if is_train else labels_val,
                    label_filename
                )

                with open(label_path, 'w') as f:
                    for ann in annotations:
                        db_class_id = ann[0]
                        x_center = ann[1]
                        y_center = ann[2]
                        width = ann[3]
                        height = ann[4]

                        # CRITICAL: Map database class_id to YOLO 0-based index
                        yolo_class_index = class_id_to_yolo_index.get(db_class_id, db_class_id)

                        f.write(f"{yolo_class_index} {x_center} {y_center} {width} {height}\n")

            # Create data.yaml with 0-based indices
            data_yaml_path = os.path.join(dataset_path, 'data.yaml')
            with open(data_yaml_path, 'w') as f:
                f.write(f"path: {dataset_path}\n")
                f.write(f"train: images/train\n")
                f.write(f"val: images/val\n\n")
                f.write(f"nc: {num_classes}\n\n")  # Number of classes
                f.write(f"names:\n")
                # Write 0-based indices with class names
                for yolo_index in range(num_classes):
                    class_name = yolo_index_to_class_info[yolo_index]
                    f.write(f"  {yolo_index}: {class_name}\n")

        return jsonify({
            'success': True,
            'dataset_path': dataset_path,
            'yaml_path': data_yaml_path,
            'stats': {
                'total_frames': total_frames,
                'train_frames': train_count,
                'val_frames': total_frames - train_count
            }
        })

    except Exception as e:
        logger.error(f"❌ Export dataset error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/start', methods=['POST'])
def start_training():
    """
    Start a new YOLO training job.

    Expects:
    - name: Training job name
    - preset: fast, balanced, or quality
    - dataset_yaml_path: Path to data.yaml

    Returns job_id immediately, training runs in background.
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

        # Initialize tables if needed
        init_training_tables()

        data = request.get_json()
        name = data.get('name', '').strip()
        preset = data.get('preset', 'balanced')
        dataset_yaml_path = data.get('dataset_yaml_path', '').strip()

        # Validate
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400

        if preset not in ['fast', 'balanced', 'quality']:
            return jsonify({'success': False, 'error': 'Invalid preset'}), 400

        if not dataset_yaml_path or not os.path.exists(dataset_yaml_path):
            return jsonify({'success': False, 'error': 'Dataset not found'}), 400

        # Use TrainingResourceManager for safe, optimized config
        # Map preset to model size for TrainingResourceManager
        model_size_map = {
            'fast': 'n',
            'balanced': 's',
            'quality': 'm'
        }
        model_size = model_size_map[preset]

        # Get optimized training config based on system resources
        training_config = TrainingResourceManager.get_training_config(preset, f'yolov8{model_size}')

        config = {
            'model_size': model_size,
            'epochs': training_config['epochs']
        }

        # Create job record
        with get_db_context() as db:
            result = db.execute(text("""
                INSERT INTO training_jobs
                (user_id, name, status, preset, model_size, epochs, dataset_yaml_path)
                VALUES (:user_id, :name, 'pending', :preset, :model_size, :epochs, :dataset_path)
                RETURNING id
            """), {
                'user_id': user_id,
                'name': name,
                'preset': preset,
                'model_size': config['model_size'],
                'epochs': config['epochs'],
                'dataset_path': dataset_yaml_path
            })

            job_id = str(result.scalar())

        # Create config file for train_worker.py
        output_dir = f"storage/models/{job_id}"
        os.makedirs(output_dir, exist_ok=True)

        progress_file = os.path.join(output_dir, 'progress.json')

        worker_config = {
            'job_id': job_id,
            'name': name,
            'dataset_yaml': dataset_yaml_path,
            'model_size': f"yolov8{config['model_size']}",
            'epochs': config['epochs'],
            'batch': training_config['batch'],
            'workers': training_config['workers'],
            'imgsz': training_config['imgsz'],
            'patience': training_config['patience'],
            'output_dir': output_dir,
            'progress_file': progress_file,
            'user_id': user_id
        }

        config_file = os.path.join(output_dir, 'config.json')
        with open(config_file, 'w') as f:
            json.dump(worker_config, f, indent=2)

        # Start training in isolated subprocess
        logger.info(f"🚀 Starting training {job_id} in isolated subprocess")
        logger.info(f"⚙️  Config: {config['epochs']} epochs, {training_config['workers']} workers, batch={training_config['batch']}")
        logger.info(f"⏱️  Estimated time: {training_config['estimated_minutes']} minutes")

        process = subprocess.Popen(
            [sys.executable, 'training/train_worker.py', config_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=os.path.dirname(os.path.abspath(__file__))
        )

        # Track process
        active_training_processes[job_id] = process

        return jsonify({
            'success': True,
            'job_id': job_id,
            'status': 'pending',
            'estimated_minutes': training_config['estimated_minutes'],
            'config': {
                'epochs': config['epochs'],
                'workers': training_config['workers'],
                'batch': training_config['batch']
            }
        })

    except Exception as e:
        logger.error(f"❌ Start training error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/status/<job_id>', methods=['GET'])
def get_training_status(job_id: str):
    """Get current status of a training job."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        user_id = payload['user_id']

        with get_db_context() as db:
            result = db.execute(text("""
                SELECT
                    id, name, status, preset, model_size, epochs,
                    progress, current_epoch, metrics, error_message,
                    started_at, completed_at, created_at
                FROM training_jobs
                WHERE id = :job_id AND user_id = :user_id
            """), {'job_id': job_id, 'user_id': user_id})

            row = result.fetchone()

            if not row:
                return jsonify({'success': False, 'error': 'Job not found'}), 404

            # Build job response from database
            job_response = {
                'id': str(row[0]),
                'name': row[1],
                'status': row[2],
                'preset': row[3],
                'model_size': row[4],
                'epochs': row[5],
                'progress': row[6] or 0,
                'current_epoch': row[7] or 0,
                'metrics': row[8],
                'error_message': row[9],
                'started_at': row[10].isoformat() if row[10] else None,
                'completed_at': row[11].isoformat() if row[11] else None,
                'created_at': row[12].isoformat() if row[12] else None
            }

            # Check progress file for real-time updates (if job is running)
            progress_file = f"storage/models/{job_id}/progress.json"
            if os.path.exists(progress_file):
                try:
                    with open(progress_file, 'r') as f:
                        progress_data = json.load(f)

                    # Override database values with progress file values
                    job_response.update({
                        'status': progress_data.get('status', job_response['status']),
                        'progress': progress_data.get('progress', job_response['progress']),
                        'current_epoch': progress_data.get('current_epoch', job_response['current_epoch']),
                        'metrics': progress_data.get('metrics', job_response['metrics']),
                        'error_message': progress_data.get('error', job_response['error_message'])
                    })
                except Exception as e:
                    logger.warning(f"Failed to read progress file for {job_id}: {e}")

            return jsonify({
                'success': True,
                'job': job_response
            })

    except Exception as e:
        logger.error(f"❌ Get training status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/stop/<job_id>', methods=['POST'])
def stop_training(job_id: str):
    """Stop a running training job."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        user_id = payload['user_id']

        with get_db_context() as db:
            # Check job status
            result = db.execute(text("""
                SELECT status FROM training_jobs
                WHERE id = :job_id AND user_id = :user_id
            """), {'job_id': job_id, 'user_id': user_id})

            row = result.fetchone()

            if not row:
                return jsonify({'success': False, 'error': 'Job not found'}), 404

            status = row[0]

            if status not in ['pending', 'running']:
                return jsonify({'success': False, 'error': f'Cannot stop job with status: {status}'}), 400

            # Update status
            db.execute(text("""
                UPDATE training_jobs
                SET status = 'stopped', completed_at = NOW()
                WHERE id = :job_id
            """), {'job_id': job_id})

            # Terminate subprocess if running
            if job_id in active_training_processes:
                process = active_training_processes[job_id]
                try:
                    process.terminate()
                    # Give it 5 seconds to terminate gracefully
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        # Force kill if it doesn't terminate
                        process.kill()
                    logger.info(f"✅ Training process {job_id} terminated")
                except Exception as e:
                    logger.warning(f"⚠️  Error terminating process {job_id}: {e}")
                finally:
                    del active_training_processes[job_id]

        return jsonify({'success': True, 'message': 'Job stopped'})

    except Exception as e:
        logger.error(f"❌ Stop training error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/history', methods=['GET'])
def get_training_history():
    """Get training history for current user."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        user_id = payload['user_id']

        with get_db_context() as db:
            result = db.execute(text("""
                SELECT
                    j.id, j.name, j.status, j.preset, j.model_size,
                    j.epochs, j.progress, j.metrics, j.error_message,
                    j.started_at, j.completed_at, j.created_at,
                    m.id as model_id, m.is_active
                FROM training_jobs j
                LEFT JOIN trained_models m ON m.job_id = j.id
                WHERE j.user_id = :user_id
                ORDER BY j.created_at DESC
                LIMIT 50
            """), {'user_id': user_id})

            jobs = []
            for row in result:
                jobs.append({
                    'id': str(row[0]),
                    'name': row[1],
                    'status': row[2],
                    'preset': row[3],
                    'model_size': row[4],
                    'epochs': row[5],
                    'progress': row[6] or 0,
                    'metrics': row[7],
                    'error_message': row[8],
                    'started_at': row[9].isoformat() if row[9] else None,
                    'completed_at': row[10].isoformat() if row[10] else None,
                    'created_at': row[11].isoformat() if row[11] else None,
                    'model_id': str(row[12]) if row[12] else None,
                    'is_active': row[13] if row[13] else False
                })

            return jsonify({
                'success': True,
                'jobs': jobs
            })

    except Exception as e:
        logger.error(f"❌ Get training history error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/models/<model_id>/activate', methods=['POST'])
def activate_model(model_id: str):
    """
    Activate a trained model.

    Deactivates all other models for the user and activates this one.
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

        with get_db_context() as db:
            # Verify model ownership
            result = db.execute(text("""
                SELECT id FROM trained_models
                WHERE id = :model_id AND user_id = :user_id
            """), {'model_id': model_id, 'user_id': user_id})

            if not result.fetchone():
                return jsonify({'success': False, 'error': 'Model not found'}), 404

            # Deactivate all user's models
            db.execute(text("""
                UPDATE trained_models
                SET is_active = FALSE
                WHERE user_id = :user_id
            """), {'user_id': user_id})

            # Activate this model
            db.execute(text("""
                UPDATE trained_models
                SET is_active = TRUE
                WHERE id = :model_id
            """), {'model_id': model_id})

        return jsonify({'success': True, 'message': 'Model activated'})

    except Exception as e:
        logger.error(f"❌ Activate model error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/models/active', methods=['GET'])
def get_active_model():
    """Get the currently active model for the user."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        user_id = payload['user_id']

        with get_db_context() as db:
            result = db.execute(text("""
                SELECT
                    m.id, m.name, m.model_path, m.model_size, m.metrics, m.created_at,
                    j.name as job_name, j.preset
                FROM trained_models m
                LEFT JOIN training_jobs j ON j.id = m.job_id
                WHERE m.user_id = :user_id AND m.is_active = TRUE
                LIMIT 1
            """), {'user_id': user_id})

            row = result.fetchone()

            if not row:
                return jsonify({'success': True, 'model': None})

            return jsonify({
                'success': True,
                'model': {
                    'id': str(row[0]),
                    'name': row[1],
                    'model_path': row[2],
                    'model_size': row[3],
                    'metrics': row[4],
                    'created_at': row[5].isoformat() if row[5] else None,
                    'job_name': row[6],
                    'preset': row[7]
                }
            })

    except Exception as e:
        logger.error(f"❌ Get active model error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================
# Admin API (Temporary - for table creation)
# ============================================================================

@app.route('/api/admin/init-training-tables', methods=['POST'])
def admin_init_training_tables():
    """
    TEMPORARY endpoint to manually create training_jobs and trained_models tables.
    Should be removed after first deployment.
    """
    try:
        # Check admin (simple token check for now)
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        with get_db_context() as db:
            # Drop existing tables if they exist (with wrong schema)
            db.execute(text("DROP TABLE IF EXISTS trained_models CASCADE"))
            db.execute(text("DROP TABLE IF EXISTS training_jobs CASCADE"))
            logger.info("✅ Dropped old training tables (if existed)")

        # Create fresh tables
        result = init_training_tables()

        if result:
            return jsonify({
                'success': True,
                'message': 'Training tables created successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create training tables'
            }), 500

    except Exception as e:
        logger.error(f"❌ Init training tables error: {e}")
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

        # Check if user is admin
        user = db.execute(text("SELECT role FROM users WHERE id = :user_id"), {'user_id': user_id}).fetchone()
        user_role = user[0] if user else 'operator'

        # Admin sees all videos, operator sees only their own
        if user_role == 'admin':
            # Admin: all videos from all users
            videos = db.execute(text("""
                SELECT id, project_id, filename, storage_path, duration_seconds,
                       frame_count, fps, uploaded_at, selected_start, selected_end,
                       total_chunks, processed_chunks, status, user_id
                FROM training_videos
                ORDER BY uploaded_at DESC
            """)).fetchall()
        else:
            # Operator: only their own videos
            videos = db.execute(text("""
                SELECT id, project_id, filename, storage_path, duration_seconds,
                       frame_count, fps, uploaded_at, selected_start, selected_end,
                       total_chunks, processed_chunks, status, user_id
                FROM training_videos
                WHERE user_id = :user_id
                ORDER BY uploaded_at DESC
            """), {'user_id': user_id}).fetchall()

        videos_with_status = []
        for video in videos:
            video_data = {
                'id': str(video[0]),
                'project_id': str(video[1]) if video[1] else None,
                'filename': video[2],
                'storage_path': video[3],
                'duration_seconds': float(video[4]) if video[4] else None,
                'frame_count': video[5],
                'fps': float(video[6]) if video[6] else None,
                'uploaded_at': video[7].isoformat() if video[7] else None,
                'selected_start': video[8],
                'selected_end': video[9],
                'total_chunks': video[10],
                'processed_chunks': video[11] or 0,
                'status': video[12] or 'pending',
                'user_id': str(video[13]) if len(video) > 13 else None
            }
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

        # Generate a UUID for the video (no project_id needed)
        import uuid
        video_id = str(uuid.uuid4())

        # Check if file was provided
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['video']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        # Save file
        from pathlib import Path
        upload_dir = Path('storage/training_videos')
        upload_dir.mkdir(parents=True, exist_ok=True)

        safe_filename = f"{video_id}_{file.filename}"
        file_path = upload_dir / safe_filename
        file.save(str(file_path))

        # Get video metadata
        import cv2
        cap = cv2.VideoCapture(str(file_path))
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration_seconds = frame_count / fps if fps and fps > 0 else None
        cap.release()

        # Insert into database (project_id is optional, set to NULL)
        db.execute(text("""
            INSERT INTO training_videos
            (id, project_id, user_id, filename, storage_path, duration_seconds,
             frame_count, fps, uploaded_at, status)
            VALUES (:id, :project_id, :user_id, :filename, :storage_path,
                    :duration_seconds, :frame_count, :fps, NOW(), 'pending')
        """), {
            'id': video_id,
            'project_id': None,  # No project required
            'user_id': user_id,
            'filename': file.filename,
            'storage_path': str(file_path),
            'duration_seconds': duration_seconds,
            'frame_count': frame_count,
            'fps': fps
        })
        db.commit()

        return jsonify({
            'success': True,
            'video_id': video_id,
            'filename': file.filename,
            'message': 'Video uploaded successfully'
        })

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

        # Verify ownership (user_id on video directly)
        check = db.execute(text("""
            SELECT id FROM training_videos
            WHERE id = :video_id AND user_id = :user_id
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


# ============================================================================
# SERVIR FRONTEND REACT EM PRODUÇÃO
# ============================================================================
import os as _os
from flask import send_from_directory as _sfd


# Correção Railway: postgres:// → postgresql://
import os as _os_db
_db_url = _os_db.environ.get('DATABASE_URL', '')
if _db_url.startswith('postgres://'):
    _os_db.environ['DATABASE_URL'] = _db_url.replace('postgres://', 'postgresql://', 1)


@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_frontend(path):
    """Serve React frontend build em produção Railway."""
    dist_dir = _os.path.join(
        _os.path.dirname(_os.path.abspath(__file__)),
        'frontend-new', 'dist'
    )
    if path and _os.path.exists(_os.path.join(dist_dir, path)):
        return _sfd(dist_dir, path)
    index = _os.path.join(dist_dir, 'index.html')
    if _os.path.exists(index):
        return _sfd(dist_dir, 'index.html')
    return jsonify({'error': 'Frontend não buildado. Executar npm run build'}), 404


# ============================================================================
# WORKERS HEALTH — Microserviços (Redis)
# ============================================================================
@app.route('/api/workers/health', methods=['GET'])
def get_workers_health():
    """Retornar status de todos os workers ativos via Redis."""
    try:
        from services.api_worker_proxy import get_workers_health
        workers = get_workers_health()
        return jsonify({
            'workers': workers,
            'total': len(workers),
            'mode': 'distributed' if workers else 'local'
        })
    except Exception as e:
        return jsonify({
            'workers': [],
            'total': 0,
            'mode': 'local',
            'error': str(e)
        }), 200


if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🚀 Starting EPI Recognition System API Server")

    # Initialize database tables
    init_database_tables()

    # Initialize training tables
    init_training_tables()

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
