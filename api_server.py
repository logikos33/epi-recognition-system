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
    verify_user_credentials, update_last_login, create_session, verify_session
)
from backend.products import ProductService
from backend.training_db import TrainingProjectDB

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
        create_session(db, user['id'], token)

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
        create_session(db, user['id'], token, ip_address=ip_address, user_agent=user_agent)

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
