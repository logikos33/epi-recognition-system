"""
API Server for EPI Recognition System
With Authentication, Database, YOLO Detection, HLS Streaming, and WebSocket Support
"""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit, join_room, leave_room
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
from backend.camera_service import CameraService
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
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet', logger=True, engineio_logger=False)

# Configuration
SECRET_KEY = os.environ.get('JWT_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("JWT_SECRET_KEY environment variable is required and must be set")
if len(SECRET_KEY) < 32:
    raise ValueError("JWT_SECRET_KEY must be at least 32 characters long")

DB_URL = os.environ.get('DATABASE_URL')
if not DB_URL:
    raise ValueError("DATABASE_URL environment variable is required")

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
# JWT Authentication Helper
# ============================================================================

def verify_jwt_token(auth_header: str) -> dict:
    """
    Verify JWT token and return payload.

    Args:
        auth_header: Authorization header value (Bearer <token>)

    Returns:
        Decoded JWT payload

    Raises:
        ValueError: If token is missing or invalid
        jwt.ExpiredSignatureError: If token has expired
        jwt.InvalidTokenError: If token is malformed
    """
    if not auth_header or not auth_header.startswith('Bearer '):
        raise ValueError('Authorization header required')

    token = auth_header.split(' ')[1]
    payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
    return payload


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

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f"✅ WebSocket client connected: {request.sid}")
    emit('connected', {'status': 'connected', 'sid': request.sid})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info(f"❌ WebSocket client disconnected: {request.sid}")


@socketio.on('subscribe_camera')
def handle_subscribe_camera(data):
    """Subscribe to detection updates for a specific camera"""
    camera_id = data.get('camera_id')
    if camera_id is None:
        emit('error', {'message': 'camera_id required'})
        return

    room = f"camera_{camera_id}"
    join_room(room)
    logger.info(f"📹 Client {request.sid} subscribed to camera {camera_id}")
    emit('subscribed', {'camera_id': camera_id, 'room': room})


@socketio.on('unsubscribe_camera')
def handle_unsubscribe_camera(data):
    """Unsubscribe from detection updates for a specific camera"""
    camera_id = data.get('camera_id')
    if camera_id is None:
        emit('error', {'message': 'camera_id required'})
        return

    room = f"camera_{camera_id}"
    leave_room(room)
    logger.info(f"📹 Client {request.sid} unsubscribed from camera {camera_id}")
    emit('unsubscribed', {'camera_id': camera_id, 'room': room})


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
    try:
        payload = verify_jwt_token(auth_header)
        user_id = payload.get('user_id')
    except (ValueError, jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        return jsonify({'error': str(e)}), 401

    # Verify camera ownership
    db = next(get_db())
    try:
        camera = CameraService.get_camera_by_id(db, camera_id)
        if not camera:
            return jsonify({'error': 'Camera not found'}), 404

        # Check if user owns this camera
        if camera['user_id'] != user_id:
            return jsonify({'error': 'Access denied'}), 403

    finally:
        db.close()

    # Validate filename to prevent path traversal
    if not filename or '..' in filename or filename.startswith('/'):
        return jsonify({'error': 'Invalid filename'}), 400

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
    try:
        payload = verify_jwt_token(auth_header)
        user_id = payload.get('user_id')
    except (ValueError, jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        return jsonify({'error': str(e)}), 401

    # Validate fps parameter
    try:
        data = request.get_json() or {}
        fps = int(data.get('fps', 5))
        if fps < 1 or fps > 30:
            return jsonify({'error': 'fps must be between 1 and 30'}), 400
    except (TypeError, ValueError):
        return jsonify({'error': 'Invalid fps value'}), 400

    # Get camera details
    db = next(get_db())
    try:
        camera = CameraService.get_camera_by_id(db, camera_id)
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
    stream_result = stream_manager.start_stream(camera_id, rtsp_url)
    if stream_result['status'] == 'error':
        return jsonify(stream_result), 500

    # Start YOLO processor
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
    try:
        payload = verify_jwt_token(auth_header)
        user_id = payload.get('user_id')
    except (ValueError, jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        return jsonify({'error': str(e)}), 401

    # Verify camera ownership before stopping
    db = next(get_db())
    try:
        camera = CameraService.get_camera_by_id(db, camera_id)
        if not camera:
            return jsonify({'error': 'Camera not found'}), 404

        if camera['user_id'] != user_id:
            return jsonify({'error': 'Access denied'}), 403
    finally:
        db.close()

    # Stop HLS stream
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
    try:
        payload = verify_jwt_token(auth_header)
        user_id = payload.get('user_id')
    except (ValueError, jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        return jsonify({'error': str(e)}), 401

    # Verify camera ownership
    db = next(get_db())
    try:
        camera = CameraService.get_camera_by_id(db, camera_id)
        if not camera:
            return jsonify({'error': 'Camera not found'}), 404

        if camera['user_id'] != user_id:
            return jsonify({'error': 'Access denied'}), 403
    finally:
        db.close()

    # Get stream status
    stream_status = stream_manager.get_stream_status(camera_id)

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
    """Get status of all active streams and detections for the authenticated user."""
    # Verify JWT token
    auth_header = request.headers.get('Authorization')
    try:
        payload = verify_jwt_token(auth_header)
        user_id = payload.get('user_id')
    except (ValueError, jwt.ExpiredSignatureError, jwt.InvalidTokenError) as e:
        return jsonify({'error': str(e)}), 401

    # Get user's cameras to filter results
    db = next(get_db())
    try:
        user_cameras = CameraService.list_cameras_by_user(db, user_id)
        user_camera_ids = {camera['id'] for camera in user_cameras}
    finally:
        db.close()

    # Get all stream statuses
    all_stream_statuses = stream_manager.get_all_streams_status()

    # Filter streams to only include user's cameras
    user_streams = {
        camera_id: status
        for camera_id, status in all_stream_statuses.get('streams', {}).items()
        if camera_id in user_camera_ids
    }

    # Get all YOLO processor statuses and filter
    all_active_cameras = yolo_processor_manager.get_active_cameras()
    user_active_cameras = [cam_id for cam_id in all_active_cameras if cam_id in user_camera_ids]

    return jsonify({
        'streams': {
            'total_active': len(user_streams),
            'streams': user_streams
        },
        'detections': {
            'total_active': len(user_active_cameras),
            'active_cameras': user_active_cameras
        }
    })


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
# YOLO Classes Management
# ============================================================================

@app.route('/api/classes', methods=['GET'])
def list_classes():
    """List all YOLO classes with statistics"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        db = next(get_db())

        query = text("""
            SELECT
                c.*,
                COUNT(DISTINCT i.id) as total_imagens,
                COUNT(DISTINCT i.id) FILTER (WHERE i.validada = true) as imagens_validadas,
                COALESCE(SUM(cd.quantidade), 0) as total_deteccoes
            FROM classes_yolo c
            LEFT JOIN imagens_treinamento i ON i.classe_id = c.id
            LEFT JOIN contagens_deteccao cd ON cd.classe_id = c.id
            WHERE c.ativo = true
            GROUP BY c.id
            ORDER BY c.class_index ASC
        """)

        result = db.execute(query)
        classes = []

        for row in result.fetchall():
            classes.append({
                'id': row[0],
                'nome': row[1],
                'descricao': row[2],
                'valor_unitario': str(row[3]),
                'unidade': row[4],
                'cor_hex': row[5],
                'ativo': row[6],
                'class_index': row[7],
                'criado_em': row[8].isoformat() if row[8] else None,
                'atualizado_em': row[9].isoformat() if row[9] else None,
                'total_imagens': row[10],
                'imagens_validadas': row[11],
                'total_deteccoes': row[12]
            })

        return jsonify({
            'success': True,
            'classes': classes
        })

    except Exception as e:
        logger.error(f"❌ List classes error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/classes', methods=['POST'])
def create_class():
    """Create a new YOLO class - updates class_index automatically"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        data = request.get_json()
        nome = data.get('nome')
        descricao = data.get('descricao')
        valor_unitario = data.get('valor_unitario', 0.00)
        unidade = data.get('unidade', 'unidade')
        cor_hex = data.get('cor_hex', '#00FF00')
        ativo = data.get('ativo', True)

        if not nome:
            return jsonify({'success': False, 'error': 'nome is required'}), 400

        db = next(get_db())

        # Get next available class_index
        max_index_query = text("""
            SELECT COALESCE(MAX(class_index), -1) + 1 AS proximo
            FROM classes_yolo
        """)
        max_index_result = db.execute(max_index_query)
        proximo_index = max_index_result.fetchone()[0]

        # Insert new class
        insert_query = text("""
            INSERT INTO classes_yolo
            (nome, descricao, valor_unitario, unidade, cor_hex, ativo, class_index, criado_em, atualizado_em)
            VALUES (:nome, :descricao, :valor_unitario, :unidade, :cor_hex, :ativo, :class_index, NOW(), NOW())
            RETURNING *
        """)

        result = db.execute(insert_query, {
            'nome': nome,
            'descricao': descricao,
            'valor_unitario': valor_unitario,
            'unidade': unidade,
            'cor_hex': cor_hex,
            'ativo': ativo,
            'class_index': proximo_index
        })

        db.commit()
        row = result.fetchone()

        logger.info(f"✅ Created YOLO class: {nome} (index {proximo_index})")

        return jsonify({
            'success': True,
            'classe': {
                'id': row[0],
                'nome': row[1],
                'descricao': row[2],
                'valor_unitario': str(row[3]),
                'unidade': row[4],
                'cor_hex': row[5],
                'ativo': row[6],
                'class_index': row[7]
            },
            'mensagem': 'Classe criada com sucesso'
        })

    except Exception as e:
        logger.error(f"❌ Create class error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/classes/<int:class_id>', methods=['PATCH'])
def update_class(class_id: int):
    """Update YOLO class configuration"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        data = request.get_json()
        valor_unitario = data.get('valor_unitario')
        unidade = data.get('unidade')
        cor_hex = data.get('cor_hex')
        ativo = data.get('ativo')
        descricao = data.get('descricao')

        if not any([valor_unitario, unidade, cor_hex, ativo is not None, descricao]):
            return jsonify({'success': False, 'error': 'No fields to update'}), 400

        db = next(get_db())

        # Build update query dynamically
        update_fields = []
        params = {'class_id': class_id}

        if valor_unitario is not None:
            update_fields.append('valor_unitario = :valor_unitario')
            params['valor_unitario'] = valor_unitario
        if unidade is not None:
            update_fields.append('unidade = :unidade')
            params['unidade'] = unidade
        if cor_hex is not None:
            update_fields.append('cor_hex = :cor_hex')
            params['cor_hex'] = cor_hex
        if ativo is not None:
            update_fields.append('ativo = :ativo')
            params['ativo'] = ativo
        if descricao is not None:
            update_fields.append('descricao = :descricao')
            params['descricao'] = descricao

        update_fields.append('atualizado_em = NOW()')

        update_query = text(f"""
            UPDATE classes_yolo
            SET {', '.join(update_fields)}
            WHERE id = :class_id
            RETURNING *
        """)

        result = db.execute(update_query, params)
        db.commit()

        updated_class = dict(result.fetchone()._mapping)

        return jsonify({
            'success': True,
            'classe': updated_class,
            'mensagem': 'Classe atualizada'
        })

    except Exception as e:
        logger.error(f"❌ Update class error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/deteccoes/registrar', methods=['POST'])
def register_detections():
    """Register YOLO detections with automatic value calculation"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        data = request.get_json()
        camera_id = data.get('camera_id')
        sessao_id = data.get('sessao_id')
        deteccoes = data.get('deteccoes', [])

        if not camera_id or not sessao_id:
            return jsonify({
                'success': False,
                'error': 'camera_id and sessao_id are required'
            }), 400

        db = next(get_db())

        # Group detections by class_index
        contagem = {}
        for det in deteccoes:
            class_index = det.get('class_index')
            if class_index is not None:
                contagem[class_index] = contagem.get(class_index, 0) + 1

        resultados = []

        for class_index, quantidade in contagem.items():
            # Get class info
            class_query = text("""
                SELECT * FROM classes_yolo
                WHERE class_index = :class_index AND ativo = true
            """)
            class_result = db.execute(class_query, {'class_index': class_index})
            classe_row = class_result.fetchone()

            if not classe_row:
                continue

            classe = dict(classe_row._mapping)

            # Insert or update detection count
            valor_total = quantidade * classe['valor_unitario']

            upsert_query = text("""
                INSERT INTO contagens_deteccao
                (camera_id, classe_id, quantidade, valor_total, sessao_id)
                VALUES (:camera_id, :classe_id, :quantidade, :valor_total, :sessao_id)
                ON CONFLICT (camera_id, classe_id, sessao_id)
                DO UPDATE SET
                    quantidade = contagens_deteccao.quantidade + EXCLUDED.quantidade,
                    detectado_em = NOW()
                RETURNING *
            """)

            result = db.execute(upsert_query, {
                'camera_id': camera_id,
                'classe_id': classe['id'],
                'quantidade': quantidade,
                'valor_total': valor_total,
                'sessao_id': sessao_id
            })

            db.commit()

            registro = dict(result.fetchone()._mapping)

            resultados.append({
                'classe': classe['nome'],
                'classe_id': classe['id'],
                'quantidade': registro['quantidade'],
                'valor_unitario': float(classe['valor_unitario']),
                'unidade': classe['unidade'],
                'valor_total': float(valor_total),
                'cor': classe['cor_hex'],
                'class_index': class_index
            })

        valor_total_sessao = sum(r['valor_total'] for r in resultados)

        return jsonify({
            'success': True,
            'sessao_id': sessao_id,
            'deteccoes': resultados,
            'valor_total_sessao': valor_total_sessao,
            'total_itens': sum(r['quantidade'] for r in resultados)
        })

    except Exception as e:
        logger.error(f"❌ Register detections error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/sessoes/<string:sessao_id>/resumo', methods=['GET'])
def get_session_summary(sessao_id: str):
    """Get summary of detections for a session"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        db = next(get_db())

        query = text("""
            SELECT
                c.nome AS classe,
                c.unidade,
                c.valor_unitario,
                c.cor_hex,
                c.class_index,
                cd.quantidade,
                cd.quantidade * c.valor_unitario AS valor_total
            FROM contagens_deteccao cd
            JOIN classes_yolo c ON c.id = cd.classe_id
            WHERE cd.sessao_id = :sessao_id
            ORDER BY cd.quantidade DESC
        """)

        result = db.execute(query, {'sessao_id': sessao_id})
        itens = [dict(row._mapping) for row in result.fetchall()]

        total_geral = sum(float(item['valor_total']) for item in itens)
        total_itens = sum(item['quantidade'] for item in itens)

        return jsonify({
            'success': True,
            'sessao_id': sessao_id,
            'itens': itens,
            'total_geral': total_geral,
            'total_itens': total_itens
        })

    except Exception as e:
        logger.error(f"❌ Get session summary error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/classes/<int:classe_id>/imagens', methods=['POST'])
def upload_training_images(classe_id: int):
    """Upload training images for a YOLO class"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        # Verify class exists
        db = next(get_db())
        class_check = text("SELECT * FROM classes_yolo WHERE id = :classe_id")
        class_result = db.execute(class_check, {'classe_id': classe_id})
        classe = class_result.fetchone()

        if not classe:
            return jsonify({'success': False, 'error': 'Classe não encontrada'}), 404

        # Check if files are present
        if 'imagens' not in request.files:
            return jsonify({'success': False, 'error': 'Nenhuma imagem enviada'}), 400

        files = request.files.getlist('imagens')
        if not files or files[0].filename == '':
            return jsonify({'success': False, 'error': 'Nenhuma imagem selecionada'}), 400

        uploaded_images = []

        # Create target directory if not exists
        target_dir = 'datasets/treinamento/images/train'
        os.makedirs(target_dir, exist_ok=True)

        for file in files:
            if file and file.filename.lower().endswith(('.jpg', '.jpeg', '.png')):
                # Generate unique filename
                import uuid as uuid_lib
                filename = secure_filename(file.filename)
                unique_filename = f"{uuid_lib.uuid4().hex}_{filename}"
                filepath = os.path.join(target_dir, unique_filename)

                # Save file
                file.save(filepath)

                # Insert into database
                insert_query = text("""
                    INSERT INTO imagens_treinamento
                    (classe_id, caminho, validada, conjunto, criado_em)
                    VALUES (:classe_id, :caminho, false, 'train', NOW())
                    RETURNING id, caminho, criado_em
                """)

                result = db.execute(insert_query, {
                    'classe_id': classe_id,
                    'caminho': filepath
                })

                db.commit()
                row = result.fetchone()

                uploaded_images.append({
                    'id': str(row[0]),
                    'caminho': row[1],
                    'validada': False,
                    'criado_em': row[2].isoformat() if row[2] else None
                })

        return jsonify({
            'success': True,
            'imagens': uploaded_images,
            'mensagem': f'{len(uploaded_images)} imagens enviadas com sucesso'
        })

    except Exception as e:
        logger.error(f"❌ Upload images error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/imagens/<int:imagem_id>/anotacao', methods=['POST'])
def save_annotation(imagem_id: int):
    """Save YOLO format annotation for a training image"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        data = request.get_json()
        anotacao_yolo = data.get('anotacao_yolo')

        if not anotacao_yolo:
            return jsonify({'success': False, 'error': 'Anotação é obrigatória'}), 400

        db = next(get_db())

        # Get image info
        img_query = text("""
            SELECT i.id, i.caminho, i.classe_id, c.nome as classe_nome
            FROM imagens_treinamento i
            JOIN classes_yolo c ON c.id = i.classe_id
            WHERE i.id = :imagem_id
        """)
        img_result = db.execute(img_query, {'imagem_id': imagem_id})
        imagem = img_result.fetchone()

        if not imagem:
            return jsonify({'success': False, 'error': 'Imagem não encontrada'}), 404

        # Save annotation to .txt file in YOLO format
        caminho_imagem = imagem[1]
        caminho_label = caminho_imagem.replace('/images/', '/labels/').replace('.jpg', '.txt').replace('.jpeg', '.txt').replace('.png', '.txt')

        # Create labels directory if not exists
        labels_dir = os.path.dirname(caminho_label)
        os.makedirs(labels_dir, exist_ok=True)

        # Write annotation file
        with open(caminho_label, 'w') as f:
            f.write(anotacao_yolo)

        # Update database
        update_query = text("""
            UPDATE imagens_treinamento
            SET anotacao_yolo = :anotacao_yolo,
                validada = true,
                conjunto = 'train'
            WHERE id = :imagem_id
            RETURNING id, validada
        """)

        result = db.execute(update_query, {
            'imagem_id': imagem_id,
            'anotacao_yolo': anotacao_yolo
        })

        db.commit()
        row = result.fetchone()

        return jsonify({
            'success': True,
            'imagem_id': str(row[0]),
            'validada': row[1],
            'caminho_label': caminho_label,
            'mensagem': 'Anotação salva com sucesso'
        })

    except Exception as e:
        logger.error(f"❌ Save annotation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/classes/<int:classe_id>/imagens', methods=['GET'])
def list_class_images(classe_id: int):
    """List all training images for a class"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        db = next(get_db())

        query = text("""
            SELECT
                id,
                caminho,
                validada,
                conjunto,
                criado_em
            FROM imagens_treinamento
            WHERE classe_id = :classe_id
            ORDER BY criado_em DESC
        """)

        result = db.execute(query, {'classe_id': classe_id})
        imagens = []

        for row in result.fetchall():
            # Convert local file path to URL
            caminho = row[1]
            filename = os.path.basename(caminho)
            image_url = f"/api/training-images/{filename}"

            imagens.append({
                'id': str(row[0]),
                'caminho': image_url,
                'caminho_local': caminho,
                'validada': row[2],
                'conjunto': row[3],
                'criado_em': row[4].isoformat() if row[4] else None
            })

        return jsonify({
            'success': True,
            'imagens': imagens,
            'total': len(imagens),
            'validadas': sum(1 for img in imagens if img['validada'])
        })

    except Exception as e:
        logger.error(f"❌ List images error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training-images/<filename>')
def serve_training_image(filename: str):
    """Serve training images from the dataset directory"""
    try:
        # Security check: ensure filename doesn't contain path traversal
        if '..' in filename or '/' in filename:
            return jsonify({'success': False, 'error': 'Invalid filename'}), 400

        # Look for the image in train directory
        image_path = os.path.join('datasets/treinamento/images/train', filename)

        if not os.path.exists(image_path):
            # Try val directory
            image_path = os.path.join('datasets/treinamento/images/val', filename)

        if not os.path.exists(image_path):
            return jsonify({'success': False, 'error': 'Image not found'}), 404

        # Send the file
        return send_from_directory(os.path.dirname(image_path), filename)

    except Exception as e:
        logger.error(f"❌ Serve training image error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/treinamento/status', methods=['GET'])
def get_yolo_training_status():
    """Get training readiness status for all classes"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        db = next(get_db())

        query = text("""
            SELECT
                c.id,
                c.nome,
                c.descricao,
                c.valor_unitario,
                c.unidade,
                c.cor_hex,
                c.class_index,
                c.ativo,
                COUNT(DISTINCT i.id) as total_imagens,
                COUNT(DISTINCT i.id) FILTER (WHERE i.validada = true) as imagens_validadas
            FROM classes_yolo c
            LEFT JOIN imagens_treinamento i ON i.classe_id = c.id
            WHERE c.ativo = true
            GROUP BY c.id
            ORDER BY c.class_index ASC
        """)

        result = db.execute(query)
        classes = []

        for row in result.fetchall():
            total_imagens = row[8] or 0
            validadas = row[9] or 0
            pronta = validadas >= 20

            classes.append({
                'id': row[0],
                'nome': row[1],
                'descricao': row[2],
                'valor_unitario': float(row[3]),
                'unidade': row[4],
                'cor_hex': row[5],
                'class_index': row[6],
                'ativo': row[7],
                'total_imagens': total_imagens,
                'imagens_validadas': validadas,
                'pronta_para_treinar': pronta,
                'progresso': (validadas / 20 * 100) if validadas < 20 else 100
            })

        todas_prontas = all(c['pronta_para_treinar'] for c in classes)
        total_validadas = sum(c['imagens_validadas'] for c in classes)

        return jsonify({
            'success': True,
            'classes': classes,
            'pode_iniciar_treinamento': todas_prontas and len(classes) >= 1,
            'total_imagens_validadas': total_validadas,
            'classes_prontas': sum(1 for c in classes if c['pronta_para_treinar']),
            'classes_total': len(classes)
        })

    except Exception as e:
        logger.error(f"❌ Get training status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/treinamento/exportar-dataset', methods=['POST'])
def export_yolo_training_dataset():
    """Export YOLO format dataset for training"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        db = next(get_db())

        # Get all active classes
        classes_query = text("""
            SELECT id, nome, class_index
            FROM classes_yolo
            WHERE ativo = true
            ORDER BY class_index ASC
        """)
        classes_result = db.execute(classes_query)
        classes = {row[0]: {'nome': row[1], 'index': row[2]} for row in classes_result.fetchall()}

        # Generate data.yaml for YOLO
        data_yaml_content = f"""# YOLO Dataset Configuration
# Generated by EPI Recognition System

path: ../datasets/treinamento
train: images/train
val: images/val

nc: {len(classes)}

names:
"""
        for classe_id, info in classes.items():
            data_yaml_content += f"  {info['index']}: {info['nome']}\n"

        # Save data.yaml
        yaml_path = 'datasets/treinamento/data.yaml'
        os.makedirs('datasets/treinamento', exist_ok=True)
        with open(yaml_path, 'w') as f:
            f.write(data_yaml_content)

        # Count validated images
        count_query = text("""
            SELECT COUNT(DISTINCT i.id)
            FROM imagens_treinamento i
            WHERE i.validada = true
        """)
        count_result = db.execute(count_query)
        total_validadas = count_result.fetchone()[0]

        return jsonify({
            'success': True,
            'dataset_config': yaml_path,
            'total_imagens': total_validadas,
            'num_classes': len(classes),
            'classes': classes,
            'mensagem': 'Dataset exportado com sucesso. Pronto para treinamento.'
        })

    except Exception as e:
        logger.error(f"❌ Export dataset error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/treinamento/classes-yaml', methods=['GET'])
def get_classes_yaml():
    """Generate and return classes.yaml content"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        db = next(get_db())

        query = text("""
            SELECT nome, class_index, cor_hex
            FROM classes_yolo
            WHERE ativo = true
            ORDER BY class_index ASC
        """)
        result = db.execute(query)

        classes_yaml = "classes:\n"
        for row in result.fetchall():
            classes_yaml += f"  {row[1]}:\n"
            classes_yaml += f"    nome: {row[0]}\n"
            classes_yaml += f"    cor: {row[2]}\n"

        return jsonify({
            'success': True,
            'classes_yaml': classes_yaml,
            'mensagem': 'Classes.yaml gerado com sucesso'
        })

    except Exception as e:
        logger.error(f"❌ Get classes yaml error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


# ============================================================================

# ============================================================================
# Video Upload and Frame Extraction Endpoints
# ============================================================================

from backend.video_service import VideoService

video_service = VideoService()


@app.route('/api/training/videos/upload', methods=['POST'])
def upload_training_video():
    """Upload a video for YOLO training dataset."""
    try:
        # Verify token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing or invalid token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        user_id = payload['user_id']

        # Check for file in request
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No video file provided'}), 400

        file = request.files['video']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        # FIX 1: Validate file extension
        allowed_extensions = {'.mp4', '.avi', '.mkv', '.mov'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'error': 'Invalid file type. Use MP4, AVI, MKV, or MOV'}), 400

        # FIX 2: Validate MIME type
        allowed_mime_types = {'video/mp4', 'video/avi', 'video/x-matroska', 'video/quicktime'}
        if file.content_type and file.content_type not in allowed_mime_types:
            return jsonify({'success': False, 'error': f'Invalid MIME type: {file.content_type}'}), 400

        # FIX 3: Validate file size (500MB limit)
        MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            return jsonify({'success': False, 'error': 'File too large. Maximum size is 500MB'}), 413

        # Get video duration using cv2.VideoCapture (reads metadata, not entire file)
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            # Stream upload to temp file (avoid loading entire file in memory)
            chunk_size = 4096
            while True:
                chunk = file.stream.read(chunk_size)
                if not chunk:
                    break
                tmp_file.write(chunk)
            tmp_file.flush()

            # Get video metadata without reading entire file
            cap = cv2.VideoCapture(tmp_file.name)
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = frame_count / fps if fps > 0 else 0
            cap.release()

            # Read file content from temp file
            with open(tmp_file.name, 'rb') as f:
                file_content = f.read()

            os.unlink(tmp_file.name)

        # Save video using service
        result = video_service.save_upload(
            db=next(get_db()),
            user_id=user_id,
            filename=file.filename,
            file_content=file_content,
            duration=duration
        )

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"❌ Upload video error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500

    except Exception as e:
        logger.error(f"❌ Upload video error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/videos', methods=['GET'])
def list_training_videos():
    """List all training videos for current user."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        db = next(get_db())
        videos = video_service.list_user_videos(db, payload['user_id'])

        return jsonify({'success': True, 'videos': videos})

    except Exception as e:
        logger.error(f"❌ List videos error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/videos/<video_id>', methods=['GET'])
def get_training_video(video_id: str):
    """Get video metadata by ID."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        db = next(get_db())
        video = video_service.get_video(db, video_id, payload['user_id'])

        if not video:
            return jsonify({'success': False, 'error': 'Video not found'}), 404

        return jsonify({'success': True, 'video': video})

    except Exception as e:
        logger.error(f"❌ Get video error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/videos/<video_id>/extract', methods=['POST'])
def extract_video_frames(video_id: str):
    """Start frame extraction for a video."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        data = request.get_json() or {}

        # If start/end provided, update selection first
        if 'start_seconds' in data and 'end_seconds' in data:
            db = next(get_db())
            video_service.update_selection(
                db=db,
                video_id=video_id,
                user_id=payload['user_id'],
                start_seconds=data['start_seconds'],
                end_seconds=data['end_seconds']
            )

        # Start extraction
        db = next(get_db())
        result = video_service.start_frame_extraction(db, video_id, payload['user_id'])

        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500

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

        db = next(get_db())
        query = text("""
            SELECT id, frame_number, chunk_number, storage_path,
                   is_annotated, annotation_count, created_at
            FROM frames
            WHERE video_id = :video_id
            ORDER BY frame_number ASC
        """)

        result = db.execute(query, {'video_id': video_id})
        rows = result.fetchall()

        frames = [
            {
                'id': str(row[0]),
                'frame_number': row[1],
                'chunk_number': row[2],
                'storage_path': row[3],
                'is_annotated': row[4],
                'annotation_count': row[5],
                'created_at': row[6].isoformat() if row[6] else None,
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
        db = next(get_db())
        query = text("""
            SELECT storage_path FROM frames WHERE id = :frame_id
        """)
        result = db.execute(query, {'frame_id': frame_id})
        row = result.fetchone()

        if not row:
            return jsonify({'success': False, 'error': 'Frame not found'}), 404

        frame_path = row[0]
        return send_from_directory(os.path.dirname(frame_path), os.path.basename(frame_path))

    except Exception as e:
        logger.error(f"❌ Serve frame image error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/videos/<video_id>', methods=['DELETE'])
def delete_training_video(video_id: str):
    """Delete a video and all its frames."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        db = next(get_db())
        success = video_service.delete_video(db, video_id, payload['user_id'])

        if success:
            return jsonify({'success': True, 'message': 'Video deleted'})
        else:
            return jsonify({'success': False, 'error': 'Video not found'}), 404

    except Exception as e:
        logger.error(f"❌ Delete video error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/api/training/images/upload', methods=['POST'])
def upload_training_image():
    """Upload individual training images (not from video)."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        user_id = payload['user_id']

        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400

        file = request.files['image']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400

        # Validate file type
        allowed_extensions = {'.jpg', '.jpeg', '.png'}
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'error': 'Invalid file type. Use .jpg, .jpeg, or .png'}), 400

        # Save image
        import uuid
        image_id = str(uuid.uuid4())
        images_dir = 'storage/training_images'
        os.makedirs(images_dir, exist_ok=True)

        image_path = os.path.join(images_dir, f"{image_id}{file_ext}")
        file.save(image_path)

        # Create frame record (without video association)
        db = next(get_db())
        query = text("""
            INSERT INTO frames (id, storage_path, video_id, frame_number, chunk_number)
            VALUES (:id, :path, NULL, 0, 0)
            RETURNING id
        """)
        result = db.execute(query, {'id': image_id, 'path': image_path})
        db.commit()

        logger.info(f"✅ Image uploaded: {file.filename}")

        return jsonify({
            'success': True,
            'frame_id': str(result.fetchone()[0]),
            'filename': file.filename,
            'image_url': f"/api/training/frames/{image_id}/image"
        })

    except Exception as e:
        logger.error(f"❌ Upload image error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/images', methods=['GET'])
def list_training_images():
    """List all individually uploaded images (not from videos)."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        db = next(get_db())
        query = text("""
            SELECT f.id, f.storage_path, f.is_annotated, f.annotation_count, f.created_at
            FROM frames f
            WHERE f.video_id IS NULL
            ORDER BY f.created_at DESC
        """)

        result = db.execute(query)
        rows = result.fetchall()

        images = [
            {
                'id': str(row[0]),
                'storage_path': row[1],
                'is_annotated': row[2],
                'annotation_count': row[3],
                'created_at': row[4].isoformat() if row[4] else None,
                'image_url': f"/api/training/frames/{str(row[0])}/image"
            }
            for row in rows
        ]

        return jsonify({'success': True, 'images': images})

    except Exception as e:
        logger.error(f"❌ List images error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/images/<image_id>', methods=['DELETE'])
def delete_training_image(image_id: str):
    """Delete an individually uploaded image."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        db = next(get_db())

        # Get image path
        get_query = text("""
            SELECT storage_path FROM frames WHERE id = :id AND video_id IS NULL
        """)
        result = db.execute(get_query, {'id': image_id})
        row = result.fetchone()

        if not row:
            return jsonify({'success': False, 'error': 'Image not found'}), 404

        # Delete file
        image_path = row[0]
        if os.path.exists(image_path):
            os.unlink(image_path)

        # Delete database record (cascade will delete annotations)
        delete_query = text("""
            DELETE FROM frames WHERE id = :id AND video_id IS NULL
        """)
        db.execute(delete_query, {'id': image_id})
        db.commit()

        logger.info(f"✅ Image deleted: {image_id}")
        return jsonify({'success': True, 'message': 'Image deleted'})

    except Exception as e:
        db.rollback()
        logger.error(f"❌ Delete image error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



# ============================================================================
# Annotation Endpoints
# ============================================================================

from backend.annotation_service import AnnotationService

annotation_service = AnnotationService()


@app.route('/api/training/frames/<frame_id>/annotations', methods=['GET'])
def get_frame_annotations(frame_id: str):
    """Get all annotations for a frame in YOLO format."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        db = next(get_db())
        annotations = annotation_service.get_frame_annotations(db, frame_id)

        return jsonify({'success': True, 'annotations': annotations})

    except Exception as e:
        logger.error(f"❌ Get annotations error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/frames/<frame_id>/annotations', methods=['POST'])
def save_frame_annotations(frame_id: str):
    """Save annotations for a frame (bulk replace)."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        data = request.get_json()
        if not data or 'annotations' not in data:
            return jsonify({'success': False, 'error': 'Missing annotations array'}), 400

        annotations = data['annotations']

        # Validate annotation format
        for ann in annotations:
            required_keys = {'class_id', 'x_center', 'y_center', 'width', 'height'}
            if not all(k in ann for k in required_keys):
                return jsonify({'success': False, 'error': 'Invalid annotation format'}), 400

        db = next(get_db())
        success = annotation_service.save_annotations(db, frame_id, annotations)

        if success:
            return jsonify({'success': True, 'message': f'Saved {len(annotations)} annotations'})
        else:
            return jsonify({'success': False, 'error': 'Failed to save annotations'}), 500

    except Exception as e:
        logger.error(f"❌ Save annotations error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/frames/<frame_id>/copy-from/<source_id>', methods=['POST'])
def copy_frame_annotations(frame_id: str, source_id: str):
    """Copy annotations from another frame."""
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        db = next(get_db())
        success = annotation_service.copy_annotations_from_frame(db, frame_id, source_id)

        if success:
            return jsonify({'success': True, 'message': 'Annotations copied'})
        else:
            return jsonify({'success': False, 'error': 'Failed to copy annotations'}), 500

    except Exception as e:
        logger.error(f"❌ Copy annotations error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/training/frames/<frame_id>/predict', methods=['POST'])
def predict_frame_annotations(frame_id: str):
    """
    Run YOLO pre-detection on a frame.

    Returns detected objects in YOLO format (normalized coordinates).
    """
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Missing token'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid token'}), 401

        # Get frame path
        db = next(get_db())
        query = text("""
            SELECT storage_path FROM frames WHERE id = :frame_id
        """)
        result = db.execute(query, {'frame_id': frame_id})
        row = result.fetchone()

        if not row:
            return jsonify({'success': False, 'error': 'Frame not found'}), 404

        frame_path = row[0]

        # Run YOLO prediction (using YOLOProcessor)
        from backend.yolo_processor import YOLOProcessor
        processor = YOLOProcessor()
        
        detections = processor.detect_objects(frame_path)
        
        # Convert to YOLO format
        annotations = []
        for det in detections:
            annotations.append({
                'class_id': det.get('class_id', 0),
                'x_center': det.get('x_center', 0.5),
                'y_center': det.get('y_center', 0.5),
                'width': det.get('width', 0.1),
                'height': det.get('height', 0.1),
                'confidence': det.get('confidence', 0.0)
            })

        logger.info(f"✅ YOLO prediction: {len(annotations)} objects detected")

        return jsonify({
            'success': True,
            'annotations': annotations,
            'model': 'yolov8n.pt'
        })

    except Exception as e:
        logger.error(f"❌ Predict annotations error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


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
    logger.info(f"🔌 WebSocket endpoint: ws://localhost:{PORT}/socket.io/")
    logger.info("=" * 60)

    # Run with SocketIO
    socketio.run(
        app,
        host='0.0.0.0',
        port=PORT,
        debug=True,
        allow_unsafe_werkzeug=True
    )
