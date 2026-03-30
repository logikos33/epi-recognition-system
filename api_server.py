"""
API Server for EPI Recognition System - FULL VERSION
With Authentication, Database, and YOLO Detection
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
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
# MIGRATION CHECKER
# ============================================

def check_and_run_migrations():
    """Check if cameras table exists and create it if needed"""
    try:
        db = SessionLocal()

        # Check if ip_cameras table exists
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'ip_cameras'
            )
        """))
        table_exists = result.fetchone()[0]

        if not table_exists:
            print("🔍 ip_cameras table not found, creating...")

            # Read migration SQL
            migration_path = os.path.join(os.path.dirname(__file__), 'migrations', '002_create_cameras_table.sql')
            if os.path.exists(migration_path):
                with open(migration_path, 'r') as f:
                    sql_content = f.read()

                # Execute migration
                db.execute(text(sql_content))
                db.commit()
                print("✅ ip_cameras table created successfully!")

                # Verify table was created
                result = db.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_name = 'ip_cameras'
                    ORDER BY ordinal_position
                """))
                columns = result.fetchall()
                print("📋 Table structure:")
                for col in columns:
                    print(f"   - {col[0]} ({col[1]}) {'nullable' if col[2] == 'YES' else 'not null'}")
            else:
                print(f"⚠️  Migration file not found: {migration_path}")
        else:
            print("✅ ip_cameras table already exists")

    except Exception as e:
        print(f"❌ Migration check failed: {e}")
    finally:
        if 'db' in locals():
            db.close()


# Run migration check at startup
check_and_run_migrations()


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
# INITIALIZATION
# ============================================

# Initialize database connection on startup
if DB_URL:
    try:
        init_db()
        print("✅ Database connection initialized")
    except Exception as e:
        print(f"⚠️  Database initialization failed: {e}")
        print("⚠️  Some endpoints may not work correctly")

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
    db = None
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

        # Get database session
        db = next(get_db())

        # Create user in database
        user = create_user(
            db, email=email, password=password,
            full_name=full_name, company_name=company_name
        )

        # Generate JWT token
        token = create_token(user['id'], user['email'])

        # Save session to database
        auth_db.create_session(db, user['id'], token)

        return jsonify({
            'success': True,
            'message': 'User registered successfully',
            'token': token,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user.get('full_name', ''),
                'company_name': user.get('company_name', '')
            }
        }), 201

    except ValueError as e:
        # Handle specific errors (like duplicate email)
        return jsonify({'success': False, 'error': str(e)}), 409
    except Exception as e:
        print(f"❌ Registration error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


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
    db = None
    try:
        data = request.get_json()

        if not data or not all(k in data for k in ['email', 'password']):
            return jsonify({'success': False, 'error': 'Email and password required'}), 400

        email = data['email'].lower().strip()
        password = data['password']

        # Get database session
        db = next(get_db())

        # Verify credentials
        user = verify_user_credentials(db, email, password)

        if not user:
            return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

        # Generate JWT token
        token = create_token(user['id'], user['email'])

        # Update last login
        update_last_login(db, user['id'])

        # Save session to database
        ip_address = request.remote_addr
        user_agent = request.headers.get('User-Agent')
        auth_db.create_session(db, user['id'], token, ip_address=ip_address, user_agent=user_agent)

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
    finally:
        if db:
            db.close()


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
    db = None
    try:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)

        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Get database session
        db = next(get_db())

        # Get user from database
        user = get_user_by_id(db, payload['user_id'])

        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        return jsonify({
            'success': True,
            'user': {
                'id': user['id'],
                'email': user['email'],
                'full_name': user.get('full_name', ''),
                'company_name': user.get('company_name', ''),
                'phone': user.get('phone', ''),
                'role': user.get('role', 'user'),
                'created_at': user.get('created_at', ''),
                'last_login': user.get('last_login', '')
            }
        }), 200

    except Exception as e:
        print(f"❌ Get user error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


# ============================================
# PRODUCTS ENDPOINTS
# ============================================

@app.route('/api/products', methods=['GET'])
def get_products():
    """
    Get products for authenticated user

    Query params:
    - skip: number of records to skip (default 0)
    - limit: max records to return (default 50)
    - category: filter by category (optional)
    - is_active: filter by active status (optional)
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

        # Get query parameters
        skip = int(request.args.get('skip', 0))
        limit = int(request.args.get('limit', 50))
        category = request.args.get('category')
        is_active_str = request.args.get('is_active')
        is_active = is_active_str.lower() == 'true' if is_active_str else None

        # Get database session
        db = next(get_db())

        # Fetch products
        products = ProductService.get_products(
            db, payload['user_id'],
            skip=skip, limit=limit,
            category=category, is_active=is_active
        )

        return jsonify({
            'success': True,
            'products': products,
            'count': len(products)
        }), 200

    except Exception as e:
        print(f"❌ Get products error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/products', methods=['POST'])
def create_product():
    """
    Create new product

    Expects:
    {
        "name": "Product Name",
        "sku": "SKU-123",
        "category": "Category",
        "description": "Description",
        "detection_threshold": 0.85,
        "volume_cm3": 1000,
        "weight_g": 500
    }
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
        if not data or 'name' not in data:
            return jsonify({'success': False, 'error': 'Product name is required'}), 400

        # Get database session
        db = next(get_db())

        # Create product
        product = ProductService.create_product(
            db, user_id=payload['user_id'],
            name=data['name'],
            sku=data.get('sku'),
            category=data.get('category'),
            description=data.get('description'),
            detection_threshold=data.get('detection_threshold', 0.85),
            volume_cm3=data.get('volume_cm3'),
            weight_g=data.get('weight_g')
        )

        return jsonify({
            'success': True,
            'message': 'Product created successfully',
            'product': product
        }), 201

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"❌ Create product error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/products/<product_id>', methods=['GET'])
def get_product(product_id):
    """Get single product by ID"""
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

        # Fetch product
        product = ProductService.get_product(db, product_id)

        if not product:
            return jsonify({'success': False, 'error': 'Product not found'}), 404

        # Verify ownership
        if product['user_id'] != payload['user_id']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        return jsonify({
            'success': True,
            'product': product
        }), 200

    except Exception as e:
        print(f"❌ Get product error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/products/<product_id>', methods=['PUT'])
def update_product(product_id):
    """
    Update product

    Expects:
    {
        "name": "Updated Name",
        "sku": "NEW-SKU",
        ...
    }
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

        # Get database session
        db = next(get_db())

        # Update product
        product = ProductService.update_product(
            db, product_id, payload['user_id'], **data
        )

        if not product:
            return jsonify({'success': False, 'error': 'Product not found or access denied'}), 404

        return jsonify({
            'success': True,
            'message': 'Product updated successfully',
            'product': product
        }), 200

    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        print(f"❌ Update product error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/products/<product_id>', methods=['DELETE'])
def delete_product(product_id):
    """Delete product (soft delete - sets is_active = False)"""
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

        # Delete product
        success = ProductService.delete_product(db, product_id, payload['user_id'])

        if not success:
            return jsonify({'success': False, 'error': 'Product not found or access denied'}), 404

        return jsonify({
            'success': True,
            'message': 'Product deleted successfully'
        }), 200

    except Exception as e:
        print(f"❌ Delete product error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


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
# TRAINING PROJECTS ENDPOINTS
# ============================================

@app.route('/api/training/projects', methods=['POST'])
def create_training_project():
    """
    Create a new training project

    Expects JSON:
    {
        "name": "Project name",
        "description": "Optional description",
        "target_classes": ["class1", "class2"]
    }
    """
    db = None
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        user_id = payload['user_id']

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Request body required'}), 400

        name = data.get('name')
        description = data.get('description')
        target_classes = data.get('target_classes', [])

        # Validate required fields
        if not name:
            return jsonify({'success': False, 'error': 'Name is required'}), 400

        if not isinstance(target_classes, list):
            return jsonify({'success': False, 'error': 'Target classes must be an array'}), 400

        if not target_classes or len(target_classes) == 0:
            return jsonify({'success': False, 'error': 'Target classes are required'}), 400

        # Get database session
        db = next(get_db())

        # Create project using TrainingProjectDB
        project = TrainingProjectDB.create_project(
            db=db,
            user_id=user_id,
            name=name,
            description=description,
            target_classes=target_classes
        )

        return jsonify({
            'success': True,
            'message': 'Training project created successfully',
            'project': project
        }), 201

    except Exception as e:
        print(f"❌ Create training project error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/training/projects', methods=['GET'])
def list_training_projects():
    """List all training projects for current user"""
    db = None
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        user_id = payload['user_id']

        # Get database session
        db = next(get_db())

        # List projects using TrainingProjectDB
        projects = TrainingProjectDB.list_user_projects(db, user_id)

        return jsonify({
            'success': True,
            'projects': projects,
            'count': len(projects)
        }), 200

    except Exception as e:
        print(f"❌ List training projects error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/training/projects/<project_id>', methods=['GET'])
def get_training_project(project_id):
    """Get a specific training project by ID"""
    db = None
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        user_id = payload['user_id']

        # Get database session
        db = next(get_db())

        # Get project using TrainingProjectDB
        project = TrainingProjectDB.get_project(db, project_id, user_id)

        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        return jsonify({
            'success': True,
            'project': project
        }), 200

    except Exception as e:
        print(f"❌ Get training project error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/training/projects/<project_id>', methods=['PUT'])
def update_training_project(project_id):
    """
    Update a training project

    Expects JSON (all fields optional):
    {
        "name": "New name",
        "description": "New description",
        "target_classes": ["class1", "class2"],
        "status": "in_progress"
    }
    """
    db = None
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        user_id = payload['user_id']

        # Get request data
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'Request body required'}), 400

        # Get database session
        db = next(get_db())

        # Update project using TrainingProjectDB
        project = TrainingProjectDB.update_project(
            db=db,
            project_id=project_id,
            user_id=user_id,
            name=data.get('name'),
            description=data.get('description'),
            target_classes=data.get('target_classes'),
            status=data.get('status')
        )

        if not project:
            return jsonify({'success': False, 'error': 'Project not found or access denied'}), 404

        return jsonify({
            'success': True,
            'message': 'Training project updated successfully',
            'project': project
        }), 200

    except Exception as e:
        print(f"❌ Update training project error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/training/projects/<project_id>', methods=['DELETE'])
def delete_training_project(project_id):
    """Delete a training project"""
    db = None
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        user_id = payload['user_id']

        # Get database session
        db = next(get_db())

        # Delete project using TrainingProjectDB
        deleted = TrainingProjectDB.delete_project(db, project_id, user_id)

        if not deleted:
            return jsonify({'success': False, 'error': 'Project not found or access denied'}), 404

        return jsonify({
            'success': True,
            'message': 'Training project deleted successfully'
        }), 200

    except Exception as e:
        print(f"❌ Delete training project error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/training/projects/<project_id>/status', methods=['PATCH'])
def update_project_status(project_id):
    """
    Update only the status of a training project

    Expects JSON:
    {
        "status": "in_progress"
    }

    Valid statuses: draft, in_progress, training, completed, failed
    """
    db = None
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        user_id = payload['user_id']

        # Get request data
        data = request.get_json()
        if not data or 'status' not in data:
            return jsonify({'success': False, 'error': 'Status field is required'}), 400

        status = data['status']

        # Validate status value
        valid_statuses = ['draft', 'in_progress', 'training', 'completed', 'failed']
        if status not in valid_statuses:
            return jsonify({
                'success': False,
                'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }), 400

        # Get database session
        db = next(get_db())

        # Update status using TrainingProjectDB
        updated = TrainingProjectDB.update_project_status(db, project_id, user_id, status)

        if not updated:
            return jsonify({'success': False, 'error': 'Project not found or access denied'}), 404

        # Get updated project
        project = TrainingProjectDB.get_project(db, project_id, user_id)

        return jsonify({
            'success': True,
            'message': 'Project status updated successfully',
            'project': project
        }), 200

    except Exception as e:
        print(f"❌ Update project status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


# ============================================
# TRAINING VIDEOS ENDPOINTS
# ============================================

@app.route('/api/training/videos', methods=['POST'])
def upload_training_video():
    """
    Upload a video to a training project

    Expects multipart/form-data:
    - video: Video file (mp4, avi, mov)
    - project_id: Project UUID

    Returns:
    - video: Video metadata
    - extracted_frames: Number of frames extracted
    """
    db = None
    temp_file = None
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        user_id = payload['user_id']

        # Check if video file is present
        if 'video' not in request.files:
            return jsonify({'success': False, 'error': 'No video file provided'}), 400

        video_file = request.files['video']
        if video_file.filename == '':
            return jsonify({'success': False, 'error': 'No video file selected'}), 400

        # Get project_id
        project_id = request.form.get('project_id')
        if not project_id:
            return jsonify({'success': False, 'error': 'project_id is required'}), 400

        # Verify project ownership
        db = next(get_db())
        project = TrainingProjectDB.get_project(db, project_id, user_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found or access denied'}), 404

        # Validate file size (max 500MB)
        video_file.seek(0, os.SEEK_END)
        file_size = video_file.tell()
        video_file.seek(0)

        MAX_SIZE = 500 * 1024 * 1024  # 500MB
        if file_size > MAX_SIZE:
            return jsonify({'success': False, 'error': f'File size exceeds 500MB limit'}), 400

        # Validate file type
        filename = secure_filename(video_file.filename)
        allowed_extensions = {'.mp4', '.avi', '.mov', '.mkv'}
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({'success': False, 'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'}), 400

        # Save to temp location
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            video_file.save(tmp_file.name)
            temp_file = tmp_file.name

        # Process video using VideoProcessor
        from backend.video_processor import VideoProcessor
        processor = VideoProcessor()

        result = processor.process_video(
            db=db,
            project_id=project_id,
            user_id=user_id,
            video_path=temp_file,
            filename=filename
        )

        if not result['success']:
            return jsonify(result), 500

        # Extract frames (1 frame per second)
        frames_result = processor.extract_frames(
            db=db,
            video_id=result['video']['id'],
            user_id=user_id,
            frames_per_second=1
        )

        return jsonify({
            'success': True,
            'video': result['video'],
            'extracted_frames': frames_result.get('extracted_frames', 0)
        }), 201

    except Exception as e:
        print(f"❌ Upload video error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        # Cleanup temp file
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass
        if db:
            db.close()


@app.route('/api/training/projects/<project_id>/videos', methods=['GET'])
def list_project_videos(project_id):
    """List all videos for a training project"""
    db = None
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        user_id = payload['user_id']

        # Get database session
        db = next(get_db())

        # Verify project ownership
        project = TrainingProjectDB.get_project(db, project_id, user_id)
        if not project:
            return jsonify({'success': False, 'error': 'Project not found or access denied'}), 404

        # List videos
        from backend.video_db import VideoService
        videos = VideoService.list_project_videos(db, project_id, user_id)

        return jsonify({
            'success': True,
            'videos': videos,
            'count': len(videos)
        }), 200

    except Exception as e:
        print(f"❌ List videos error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/training/videos/<video_id>', methods=['GET'])
def get_training_video(video_id):
    """Get a specific video by ID"""
    db = None
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        user_id = payload['user_id']

        # Get database session
        db = next(get_db())

        # Get video
        from backend.video_db import VideoService
        video = VideoService.get_video(db, video_id, user_id)

        if not video:
            return jsonify({'success': False, 'error': 'Video not found or access denied'}), 404

        return jsonify({
            'success': True,
            'video': video
        }), 200

    except Exception as e:
        print(f"❌ Get video error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/training/videos/<video_id>', methods=['DELETE'])
def delete_training_video(video_id):
    """Delete a training video (cascade deletes frames and annotations)"""
    db = None
    try:
        # Verify JWT token
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        user_id = payload['user_id']

        # Get database session
        db = next(get_db())

        # Delete video
        from backend.video_db import VideoService
        deleted = VideoService.delete_video(db, video_id, user_id)

        if not deleted:
            return jsonify({'success': False, 'error': 'Video not found or access denied'}), 404

        return jsonify({
            'success': True,
            'message': 'Video deleted successfully'
        }), 200

    except Exception as e:
        print(f"❌ Delete video error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


# ============================================
# ANNOTATION ENDPOINTS
# ============================================

@app.route('/api/training/annotations', methods=['POST'])
def create_annotation():
    """Create a new annotation for a frame"""
    try:
        # Verify authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        user_id = payload['user_id']
        data = request.get_json()

        # Validate required fields
        required_fields = ['frame_id', 'class_name', 'bbox_x', 'bbox_y', 'bbox_width', 'bbox_height']
        for field in required_fields:
            if field not in data:
                return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400

        # Get database session
        db = next(get_db())

        # Create annotation
        from backend.annotation_db import AnnotationDB
        annotation_db = AnnotationDB()

        annotation = annotation_db.create_annotation(
            db=db,
            frame_id=data['frame_id'],
            class_name=data['class_name'],
            bbox_x=float(data['bbox_x']),
            bbox_y=float(data['bbox_y']),
            bbox_width=float(data['bbox_width']),
            bbox_height=float(data['bbox_height']),
            is_ai_generated=data.get('is_ai_generated', False),
            confidence=data.get('confidence'),
            created_by=user_id
        )

        # Mark frame as annotated
        from sqlalchemy import text
        db.execute(text("""
            UPDATE training_frames
            SET is_annotated = TRUE
            WHERE id = :frame_id
        """), {'frame_id': data['frame_id']})
        db.commit()

        return jsonify({
            'success': True,
            'annotation': annotation
        }), 201

    except Exception as e:
        print(f"❌ Create annotation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/training/frames/<frame_id>/annotations', methods=['GET'])
def get_frame_annotations(frame_id):
    """Get all annotations for a specific frame"""
    try:
        # Verify authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Get database session
        db = next(get_db())

        # Get annotations
        from backend.annotation_db import AnnotationDB
        annotation_db = AnnotationDB()

        annotations = annotation_db.get_frame_annotations(db, frame_id)

        return jsonify({
            'success': True,
            'annotations': annotations
        }), 200

    except Exception as e:
        print(f"❌ Get annotations error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/training/annotations/<annotation_id>', methods=['PUT'])
def update_annotation(annotation_id):
    """Update an existing annotation"""
    try:
        # Verify authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        data = request.get_json()

        # Get database session
        db = next(get_db())

        # Update annotation
        from backend.annotation_db import AnnotationDB
        annotation_db = AnnotationDB()

        updated = annotation_db.update_annotation(
            db=db,
            annotation_id=annotation_id,
            class_name=data.get('class_name'),
            bbox_x=data.get('bbox_x'),
            bbox_y=data.get('bbox_y'),
            bbox_width=data.get('bbox_width'),
            bbox_height=data.get('bbox_height'),
            is_reviewed=data.get('is_reviewed')
        )

        if not updated:
            return jsonify({'success': False, 'error': 'Annotation not found'}), 404

        return jsonify({
            'success': True,
            'message': 'Annotation updated successfully'
        }), 200

    except Exception as e:
        print(f"❌ Update annotation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/training/annotations/<annotation_id>', methods=['DELETE'])
def delete_annotation(annotation_id):
    """Delete an annotation"""
    try:
        # Verify authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        # Get database session
        db = next(get_db())

        # Delete annotation
        from backend.annotation_db import AnnotationDB
        annotation_db = AnnotationDB()

        deleted = annotation_db.delete_annotation(db, annotation_id)

        if not deleted:
            return jsonify({'success': False, 'error': 'Annotation not found'}), 404

        return jsonify({
            'success': True,
            'message': 'Annotation deleted successfully'
        }), 200

    except Exception as e:
        print(f"❌ Delete annotation error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


# ============================================
# YOLO EXPORT ENDPOINTS
# ============================================

@app.route('/api/training/projects/<project_id>/export-dataset', methods=['POST'])
def export_training_dataset(project_id):
    """Export annotations to YOLO format"""
    try:
        # Verify authentication
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'success': False, 'error': 'Authorization token required'}), 401

        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

        user_id = payload['user_id']
        data = request.get_json()
        train_val_split = data.get('train_val_split', 0.8)

        # Verify project ownership
        db = next(get_db())
        from backend.training_db import TrainingProjectDB
        project_db = TrainingProjectDB()
        project = project_db.get_project(db, project_id, user_id)

        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        # Create temp directory for export
        import tempfile
        export_dir = tempfile.mkdtemp()

        # Export dataset
        from backend.yolo_exporter import YOLOExporter
        exporter = YOLOExporter()

        result = exporter.export_project(db, project_id, export_dir, train_val_split)

        if not result['success']:
            return jsonify(result), 500

        # Create ZIP file
        import zipfile
        zip_path = os.path.join(export_dir, 'yolo_dataset.zip')

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(export_dir):
                for file in files:
                    if file != 'yolo_dataset.zip':
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, export_dir)
                        zipf.write(file_path, arcname)

        # TODO: Upload ZIP to MinIO and return download URL
        # For now, just return metadata
        return jsonify({
            'success': True,
            'train_samples': result['train_samples'],
            'val_samples': result['val_samples'],
            'message': 'Dataset exported successfully (ZIP creation not yet implemented)'
        }), 200

    except Exception as e:
        print(f"❌ Export dataset error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


# ============================================
# YOLO TRAINING ENDPOINTS
# ============================================

@app.route('/api/training/projects/<project_id>/train', methods=['POST'])
def start_training(project_id):
    """
    Start YOLO training for a project

    Request body:
    {
        "config": {
            "epochs": 100,
            "batch_size": 16,
            "image_size": 640,
            "learning_rate": 0.01,
            "optimizer": "sgd",
            "device": "cpu",
            "workers": 8
        },
        "augmentation": {
            "hsv_h": 0.015,
            "hsv_s": 0.7,
            "hsv_v": 0.4,
            "degrees": 0.0,
            "translate": 0.1,
            "scale": 0.5,
            "flipud": 0.0,
            "fliplr": 0.5,
            "mosaic": 1.0,
            "mixup": 0.0
        },
        "model": "yolov8n.pt"
    }
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'success': False, 'error': 'Missing authorization header'}), 401

    token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    db = None
    try:
        db = next(get_db())

        # Verify project ownership
        project_db = TrainingProjectDB()
        project = project_db.get_project(db, project_id, payload['user_id'])

        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        # Get request data
        data = request.get_json() or {}
        config = data.get('config', {})
        augmentation = data.get('augmentation', {})
        model = data.get('model', 'yolov8n.pt')

        # Validate required config
        if not config.get('epochs'):
            return jsonify({'success': False, 'error': 'epochs is required'}), 400

        # Import trainer
        from backend.yolo_trainer import YOLOTrainer

        trainer = YOLOTrainer()
        result = trainer.start_training(
            db=db,
            project_id=project_id,
            config=config,
            augmentation=augmentation,
            model=model
        )

        if not result['success']:
            return jsonify(result), 500

        return jsonify({
            'success': True,
            'training_id': result['training_id'],
            'message': result.get('message', 'Training started successfully')
        }), 200

    except Exception as e:
        print(f"❌ Start training error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/training/projects/<project_id>/training-status', methods=['GET'])
def get_training_status(project_id):
    """
    Get training job status for a project

    Returns:
    {
        "success": true,
        "status": "running",  # not_started, running, completed, failed
        "model": {
            "id": "...",
            "model_name": "...",
            "map50": 0.85,
            "precision": 0.88,
            "recall": 0.82,
            ...
        }
    }
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'success': False, 'error': 'Missing authorization header'}), 401

    token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    db = None
    try:
        db = next(get_db())

        # Verify project ownership
        project_db = TrainingProjectDB()
        project = project_db.get_project(db, project_id, payload['user_id'])

        if not project:
            return jsonify({'success': False, 'error': 'Project not found'}), 404

        # Get training status
        from backend.yolo_trainer import YOLOTrainer

        trainer = YOLOTrainer()
        result = trainer.get_training_status(db, project_id)

        if not result['success']:
            return jsonify(result), 500

        return jsonify(result), 200

    except Exception as e:
        print(f"❌ Get training status error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


@app.route('/api/training/models/<model_id>/activate', methods=['POST'])
def activate_model(model_id):
    """
    Set a trained model as active for its project

    Only the project owner can activate models
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header:
        return jsonify({'success': False, 'error': 'Missing authorization header'}), 401

    token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    db = None
    try:
        db = next(get_db())

        # Activate model
        from backend.yolo_trainer import YOLOTrainer

        trainer = YOLOTrainer()
        result = trainer.activate_model(db, model_id, payload['user_id'])

        if not result['success']:
            return jsonify(result), 400 if 'error' in result else 404

        return jsonify({
            'success': True,
            'message': f'Model {result.get("model_name")} activated successfully'
        }), 200

    except Exception as e:
        print(f"❌ Activate model error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        if db:
            db.close()


# ============================================
# CAMERA MANAGEMENT ENDPOINTS
# ============================================

@app.route('/api/cameras', methods=['GET'])
def list_cameras():
    """List all cameras"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        db = next(get_db())
        cameras = CameraService.list_cameras(db)
        return jsonify({
            'success': True,
            'cameras': cameras
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/cameras', methods=['POST'])
def create_camera():
    """Create a new camera"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        data = request.get_json()
        bay_id = data.get('bay_id')
        name = data.get('name')
        rtsp_url = data.get('rtsp_url')

        if not bay_id or not name:
            return jsonify({
                'success': False,
                'error': 'bay_id and name are required'
            }), 400

        db = next(get_db())
        camera = CameraService.create_camera(
            db=db,
            bay_id=bay_id,
            name=name,
            rtsp_url=rtsp_url
        )

        if camera:
            return jsonify({
                'success': True,
                'camera': camera
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create camera'
            }), 500

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/cameras/<int:camera_id>', methods=['GET'])
def get_camera(camera_id):
    """Get camera by ID"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        db = next(get_db())
        camera = CameraService.get_camera_by_id(db, camera_id)

        if camera:
            return jsonify({
                'success': True,
                'camera': camera
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Camera not found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/cameras/<int:camera_id>', methods=['PUT'])
def update_camera(camera_id):
    """Update camera"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        data = request.get_json()
        db = next(get_db())
        camera = CameraService.update_camera(
            db=db,
            camera_id=camera_id,
            name=data.get('name'),
            rtsp_url=data.get('rtsp_url'),
            is_active=data.get('is_active'),
            position_order=data.get('position_order')
        )

        if camera:
            return jsonify({
                'success': True,
                'camera': camera
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Camera not found or update failed'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/cameras/<int:camera_id>', methods=['DELETE'])
def delete_camera(camera_id):
    """Delete camera"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        db = next(get_db())
        success = CameraService.delete_camera(db, camera_id)

        if success:
            return jsonify({
                'success': True,
                'message': 'Camera deleted'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Camera not found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/cameras/by-bay/<int:bay_id>', methods=['GET'])
def get_cameras_by_bay(bay_id):
    """Get all cameras for a specific bay"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        db = next(get_db())
        cameras = CameraService.get_cameras_by_bay(db, bay_id)
        return jsonify({
            'success': True,
            'cameras': cameras
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/bays', methods=['GET'])
def list_bays():
    """List all bays"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        db = next(get_db())
        result = db.execute(text("SELECT * FROM bays ORDER BY id"))
        rows = result.fetchall()

        bays = []
        for row in rows:
            bays.append({
                'id': row[0],
                'name': row[1],
                'location': row[2],
                'scale_integration': row[3],
                'created_at': row[4].isoformat() if row[4] else None
            })

        return jsonify({
            'success': True,
            'bays': bays
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================
# FUELING SESSIONS API
# ============================================

@app.route('/api/sessions', methods=['POST'])
def create_fueling_session():
    """Create a new fueling session with duplicate prevention"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        data = request.get_json()
        bay_id = data.get('bay_id')
        camera_id = data.get('camera_id')
        license_plate = data.get('license_plate')

        if not bay_id or not camera_id or not license_plate:
            return jsonify({
                'success': False,
                'error': 'bay_id, camera_id, and license_plate are required'
            }), 400

        db = next(get_db())

        # Check for duplicate session (same camera + license plate within 30 seconds)
        duplicate_check = text("""
            SELECT id, truck_entry_time
            FROM fueling_sessions
            WHERE camera_id = :camera_id
              AND license_plate = :license_plate
              AND truck_entry_time > NOW() - INTERVAL '30 seconds'
              AND status = 'active'
            ORDER BY truck_entry_time DESC
            LIMIT 1
        """)

        duplicate_result = db.execute(duplicate_check, {
            'camera_id': camera_id,
            'license_plate': license_plate
        }).fetchone()

        if duplicate_result:
            # Duplicate detected - return existing session instead of creating new one
            existing_session_id = duplicate_result[0]
            existing_session_query = text("""
                SELECT
                    id, bay_id, camera_id, license_plate,
                    truck_entry_time, products_counted,
                    final_weight, status
                FROM fueling_sessions
                WHERE id = :session_id
            """)

            session_result = db.execute(existing_session_query, {'session_id': existing_session_id})
            session = dict(session_result.fetchone()._mapping)

            return jsonify({
                'success': True,
                'session': session,
                'duplicate': True,
                'message': 'Using existing session from 30 seconds ago'
            }), 200

        # No duplicate - create new session
        import uuid
        session_id = str(uuid.uuid4())

        insert_query = text("""
            INSERT INTO fueling_sessions
            (id, bay_id, camera_id, license_plate, truck_entry_time, status)
            VALUES (:id, :bay_id, :camera_id, :license_plate, NOW(), 'active')
            RETURNING id, bay_id, camera_id, license_plate, truck_entry_time, status
        """)

        result = db.execute(insert_query, {
            'id': session_id,
            'bay_id': bay_id,
            'camera_id': camera_id,
            'license_plate': license_plate
        })

        db.commit()

        new_session = dict(result.fetchone()._mapping)

        # Clean up old sessions (older than 7 days)
        cleanup_query = text("""
            DELETE FROM fueling_sessions
            WHERE truck_entry_time < NOW() - INTERVAL '7 days'
              AND status IN ('completed', 'paused')
        """)

        cleanup_result = db.execute(cleanup_query)
        db.commit()

        if cleanup_result.rowcount > 0:
            print(f"[Storage Optimization] Cleaned up {cleanup_result.rowcount} old sessions")

        return jsonify({
            'success': True,
            'session': new_session,
            'duplicate': False
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sessions', methods=['GET'])
def list_fueling_sessions():
    """List fueling sessions with optional filters"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        # Get query parameters
        bay_id = request.args.get('bay_id', type=int)
        status = request.args.get('status')
        limit = request.args.get('limit', 50, type=int)
        camera_id = request.args.get('camera_id', type=int)

        db = next(get_db())

        # Build the base query
        query_conditions = []
        query_params = {}

        if bay_id is not None:
            query_conditions.append("fs.bay_id = :bay_id")
            query_params['bay_id'] = bay_id

        if status:
            query_conditions.append("fs.status = :status")
            query_params['status'] = status

        if camera_id is not None:
            query_conditions.append("fs.camera_id = :camera_id")
            query_params['camera_id'] = camera_id

        where_clause = f"WHERE {' AND '.join(query_conditions)}" if query_conditions else ""

        # Build the complete query
        query = text(f"""
            SELECT
                fs.id,
                fs.bay_id,
                fs.camera_id,
                fs.license_plate,
                fs.truck_entry_time,
                fs.products_counted,
                fs.final_weight,
                fs.status,
                b.name as bay_name,
                c.name as camera_name
            FROM fueling_sessions fs
            LEFT JOIN bays b ON fs.bay_id = b.id
            LEFT JOIN cameras c ON fs.camera_id = c.id
            {where_clause}
            ORDER BY fs.truck_entry_time DESC
            LIMIT :limit
        """)

        query_params['limit'] = limit

        result = db.execute(query, query_params)
        sessions = [dict(row._mapping) for row in result.fetchall()]

        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sessions/batch', methods=['GET'])
def list_fueling_sessions_batch():
    """Batch query - fetch latest session for each camera in one query"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        # Get camera IDs from query parameter (comma-separated)
        camera_ids_str = request.args.get('camera_ids', '')
        if not camera_ids_str:
            return jsonify({'success': False, 'error': 'camera_ids parameter required'}), 400

        camera_ids = [int(id.strip()) for id in camera_ids_str.split(',') if id.strip()]

        if not camera_ids:
            return jsonify({'success': False, 'error': 'No valid camera IDs provided'}), 400

        db = next(get_db())

        # Batch query using DISTINCT ON with ANY array
        query = text("""
            WITH ranked_sessions AS (
                SELECT
                    fs.id,
                    fs.bay_id,
                    fs.camera_id,
                    fs.license_plate,
                    fs.truck_entry_time,
                    fs.products_counted,
                    fs.final_weight,
                    fs.status,
                    ROW_NUMBER() OVER (
                        PARTITION BY fs.camera_id
                        ORDER BY fs.truck_entry_time DESC
                    ) as rn
                FROM fueling_sessions fs
                WHERE fs.camera_id = ANY(:camera_ids)
                  AND fs.status = 'active'
                )
                SELECT
                    id, bay_id, camera_id, license_plate,
                    truck_entry_time, products_counted,
                    final_weight, status
                FROM ranked_sessions
                WHERE rn = 1
                ORDER BY camera_id
        """)

        result = db.execute(query, {'camera_ids': camera_ids})
        sessions = [dict(row._mapping) for row in result.fetchall()]

        return jsonify({
            'success': True,
            'sessions': sessions
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sessions/<session_id>', methods=['GET'])
def get_fueling_session(session_id):
    """Get fueling session by ID"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        db = next(get_db())
        session = FuelingSessionService.get_session_by_id(db, session_id)

        if session:
            return jsonify({
                'success': True,
                'session': session
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sessions/<session_id>', methods=['PUT'])
def update_fueling_session(session_id):
    """Update fueling session"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        data = request.get_json()
        db = next(get_db())
        session = FuelingSessionService.update_session(
            db=db,
            session_id=session_id,
            license_plate=data.get('license_plate'),
            truck_exit_time=data.get('truck_exit_time'),
            duration_seconds=data.get('duration_seconds'),
            final_weight=data.get('final_weight'),
            status=data.get('status')
        )

        if session:
            return jsonify({
                'success': True,
                'session': session
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Session not found or update failed'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sessions/<session_id>/complete', methods=['POST'])
def complete_fueling_session(session_id):
    """Mark fueling session as completed"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        data = request.get_json(force=True, silent=True) or {}
        truck_exit_time = data.get('truck_exit_time')

        db = next(get_db())
        session = FuelingSessionService.complete_session(
            db=db,
            session_id=session_id,
            truck_exit_time=truck_exit_time
        )

        if session:
            return jsonify({
                'success': True,
                'session': session
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Session not found or complete failed'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sessions/<session_id>/products', methods=['POST'])
def add_session_counted_product(session_id):
    """Add a counted product to a session"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        data = request.get_json()
        product_type = data.get('product_type')
        quantity = data.get('quantity')
        confidence = data.get('confidence')
        confirmed_by_user = data.get('confirmed_by_user', False)

        if not product_type or quantity is None:
            return jsonify({
                'success': False,
                'error': 'product_type and quantity are required'
            }), 400

        db = next(get_db())
        product = FuelingSessionService.add_counted_product(
            db=db,
            session_id=session_id,
            product_type=product_type,
            quantity=quantity,
            confidence=confidence,
            confirmed_by_user=confirmed_by_user
        )

        if product:
            return jsonify({
                'success': True,
                'product': product
            }), 201
        else:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/sessions/<session_id>/products', methods=['GET'])
def get_session_products_list(session_id):
    """Get all counted products for a session"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    try:
        db = next(get_db())
        products = FuelingSessionService.get_session_products(db, session_id)

        return jsonify({
            'success': True,
            'products': products
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================
# OCR ENDPOINTS
# ============================================

@app.route('/api/ocr/recognize-license-plate', methods=['POST'])
def recognize_license_plate():
    """
    Recognize license plate from image using OCR

    Expects multipart/form-data:
    - image: Image file (jpg, png, jpeg, bmp)

    Returns:
    {
        "success": true,
        "license_plate": "ABC-1234",
        "confidence": 89.5,
        "valid": true
    }
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Authorization token required'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid or expired token'}), 401

    temp_file = None
    try:
        # Check if image file is present
        if 'image' not in request.files:
            return jsonify({'success': False, 'error': 'No image file provided'}), 400

        image_file = request.files['image']
        if image_file.filename == '':
            return jsonify({'success': False, 'error': 'No image file selected'}), 400

        # Validate file type
        filename = secure_filename(image_file.filename)
        allowed_extensions = {'.jpg', '.jpeg', '.png', '.bmp'}
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in allowed_extensions:
            return jsonify({
                'success': False,
                'error': f'Invalid file type. Allowed: {", ".join(allowed_extensions)}'
            }), 400

        # Save to temp location
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_ext) as tmp_file:
            image_file.save(tmp_file.name)
            temp_file = tmp_file.name

        # Process with OCRService
        result = OCRService.recognize_license_plate(temp_file)

        # Return result
        return jsonify({
            'success': True,
            'license_plate': result['license_plate'],
            'confidence': result['confidence'],
            'valid': result['valid']
        }), 200

    except Exception as e:
        print(f"❌ OCR recognition error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        # Cleanup temp file
        if temp_file and os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except:
                pass


# ============================================

# ============================================
# YOLO CLASSES MANAGEMENT API
# ============================================

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
        classes = [dict(row._mapping) for row in result.fetchall()]

        return jsonify({
            'success': True,
            'classes': classes
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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

        if not nome:
            return jsonify({
                'success': False,
                'error': 'nome is required'
            }), 400

        db = next(get_db())

        # Get next available class_index
        max_index_query = text("""
            SELECT COALESCE(MAX(class_index), -1) + 1 AS proximo
            FROM classes_yolo
        """)
        result = db.execute(max_index_query)
        class_index = result.fetchone()[0]

        # Insert new class
        insert_query = text("""
            INSERT INTO classes_yolo
            (nome, descricao, valor_unitario, unidade, cor_hex, class_index)
            VALUES (:nome, :descricao, :valor_unitario, :unidade, :cor_hex, :class_index)
            RETURNING *
        """)

        result = db.execute(insert_query, {
            'nome': nome,
            'descricao': descricao,
            'valor_unitario': valor_unitario,
            'unidade': unidade,
            'cor_hex': cor_hex,
            'class_index': class_index
        })

        db.commit()
        new_class = dict(result.fetchone()._mapping)

        return jsonify({
            'success': True,
            'classe': new_class,
            'mensagem': f'Classe "{nome}" adicionada como índice {class_index}.'
        }), 201

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        descricao = data.get('descricao')
        cor_hex = data.get('cor_hex')
        ativo = data.get('ativo')

        db = next(get_db())

        update_query = text("""
            UPDATE classes_yolo SET
                valor_unitario = COALESCE(:valor_unitario, valor_unitario),
                unidade = COALESCE(:unidade, unidade),
                descricao = COALESCE(:descricao, descricao),
                cor_hex = COALESCE(:cor_hex, cor_hex),
                ativo = COALESCE(:ativo, ativo),
                atualizado_em = NOW()
            WHERE id = :class_id
            RETURNING *
        """)

        result = db.execute(update_query, {
            'class_id': class_id,
            'valor_unitario': valor_unitario,
            'unidade': unidade,
            'descricao': descricao,
            'cor_hex': cor_hex,
            'ativo': ativo
        })

        db.commit()

        if result.rowcount == 0:
            return jsonify({
                'success': False,
                'error': 'Class not found'
            }), 404

        updated_class = dict(result.fetchone()._mapping)

        return jsonify({
            'success': True,
            'classe': updated_class,
            'mensagem': 'Classe atualizada'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
