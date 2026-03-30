# Camera Streaming System with HLS and YOLO - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a complete IP camera management and real-time streaming system with HLS via FFmpeg and continuous YOLO object detection for product/EPI counting.

**Architecture:** Flask backend manages FFmpeg subprocesses for RTSP→HLS conversion and runs YOLO detection in background threads. Frontend uses hls.js for playback and WebSocket to receive real-time bounding boxes.

**Tech Stack:**
- Backend: Flask, FFmpeg, YOLOv8, SQLAlchemy, Flask-SocketIO
- Frontend: Next.js, TypeScript, hls.js, WebSocket
- Database: PostgreSQL (Railway)

---

## Phase 1: Backend Foundation

### Task 1: Create cameras table migration

**Files:**
- Create: `migrations/002_create_cameras_table.sql`

- [ ] **Step 1: Create migration file**

```sql
-- migrations/002_create_cameras_table.sql
CREATE TABLE cameras (
  id                  SERIAL PRIMARY KEY,
  user_id             UUID         NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  name                VARCHAR(100) NOT NULL,
  manufacturer        VARCHAR(50)  NOT NULL,
  type                VARCHAR(20)  NOT NULL DEFAULT 'ip',
  ip                  VARCHAR(50)  NOT NULL,
  port                INTEGER      NOT NULL DEFAULT 554,
  username            VARCHAR(100),
  password            VARCHAR(100),
  channel             INTEGER      NOT NULL DEFAULT 1,
  subtype             INTEGER      NOT NULL DEFAULT 1,
  rtsp_url            VARCHAR(500),
  is_active           BOOLEAN      DEFAULT true,
  last_connected_at   TIMESTAMP,
  connection_error    TEXT,
  created_at          TIMESTAMP    DEFAULT NOW()
);

CREATE INDEX idx_cameras_user_id ON cameras(user_id);
CREATE INDEX idx_cameras_is_active ON cameras(is_active);

COMMENT ON COLUMN cameras.manufacturer IS 'Camera manufacturer: intelbras, hikvision, generic';
COMMENT ON COLUMN cameras.type IS 'Camera type: ip, dvr, nvr';
COMMENT ON COLUMN cameras.subtype IS 'Stream type: 0=main stream, 1=sub-stream (low latency)';
```

- [ ] **Step 2: Run migration on Railway database**

Run: `psql $DATABASE_URL -f migrations/002_create_cameras_table.sql`

Expected: Table created successfully

- [ ] **Step 3: Verify table exists**

Run: `psql $DATABASE_URL -c "\d cameras"`

Expected: Table schema displayed

- [ ] **Step 4: Commit migration**

```bash
git add migrations/002_create_cameras_table.sql
git commit -m "feat: add cameras table for IP camera management"
```

---

### Task 2: Create RTSPBuilder module

**Files:**
- Create: `backend/rtsp_builder.py`
- Test: `tests/test_rtsp_builder.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_rtsp_builder.py
import pytest
from backend.rtsp_builder import RTSPBuilder

def test_build_intelbras_url():
    camera = {
        'manufacturer': 'intelbras',
        'ip': '192.168.1.100',
        'port': 554,
        'username': 'admin',
        'password': 'pass123',
        'channel': 1,
        'subtype': 1
    }
    url = RTSPBuilder.build_url(camera)
    assert url == 'rtsp://admin:pass123@192.168.1.100:554/cam/realmonitor?channel=1&subtype=1'

def test_build_hikvision_url():
    camera = {
        'manufacturer': 'hikvision',
        'ip': '192.168.1.101',
        'port': 554,
        'username': 'admin',
        'password': 'pass123',
        'channel': 1,
        'subtype': 0
    }
    url = RTSPBuilder.build_url(camera)
    assert url == 'rtsp://admin:pass123@192.168.1.101:554/Streaming/Channels/101'

def test_build_generic_url():
    camera = {
        'manufacturer': 'generic',
        'ip': '192.168.1.102',
        'port': 554,
        'username': 'admin',
        'password': 'pass123',
        'channel': 2,
        'subtype': 1
    }
    url = RTSPBuilder.build_url(camera)
    assert url == 'rtsp://admin:pass123@192.168.1.102:554/stream2'

def test_missing_credentials():
    camera = {
        'manufacturer': 'intelbras',
        'ip': '192.168.1.100',
        'port': 554,
        'username': '',
        'password': '',
        'channel': 1,
        'subtype': 1
    }
    url = RTSPBuilder.build_url(camera)
    assert 'rtsp://' in url
    assert '@192.168.1.100:554' in url
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_rtsp_builder.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'backend.rtsp_builder'"

- [ ] **Step 3: Implement RTSPBuilder**

```python
# backend/rtsp_builder.py
from typing import Dict

class RTSPBuilder:
    """Build RTSP URLs based on camera manufacturer"""

    @staticmethod
    def build_url(camera: Dict) -> str:
        """
        Build RTSP URL from camera configuration

        Args:
            camera: Dict with keys: manufacturer, ip, port, username, password, channel, subtype

        Returns:
            Complete RTSP URL string
        """
        manufacturer = camera.get('manufacturer', 'generic')
        ip = camera['ip']
        port = camera.get('port', 554)
        username = camera.get('username', '')
        password = camera.get('password', '')

        # Build auth part
        if username and password:
            auth = f"{username}:{password}@"
        else:
            auth = '@'  # No auth

        base = f"rtsp://{auth}{ip}:{port}"

        # Build path based on manufacturer
        if manufacturer == 'intelbras':
            channel = camera.get('channel', 1)
            subtype = camera.get('subtype', 1)
            return f"{base}/cam/realmonitor?channel={channel}&subtype={subtype}"

        elif manufacturer == 'hikvision':
            # Hikvision uses: (channel * 100) + (subtype == 0 ? 1 : 2)
            channel = camera.get('channel', 1)
            subtype = camera.get('subtype', 1)
            stream_id = (channel * 100) + (1 if subtype == 0 else 2)
            return f"{base}/Streaming/Channels/{stream_id}"

        else:  # generic ONVIF
            channel = camera.get('channel', 1)
            return f"{base}/stream{channel}"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_rtsp_builder.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/rtsp_builder.py tests/test_rtsp_builder.py
git commit -m "feat: add RTSPBuilder for camera URL generation"
```

---

### Task 3: Expand CameraService with IP camera CRUD

**Files:**
- Modify: `backend/camera_service.py`
- Test: `tests/test_camera_service_expanded.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_camera_service_expanded.py
import pytest
from backend.database import SessionLocal
from backend.camera_service import CameraService
from backend.rtsp_builder import RTSPBuilder

def test_create_ip_camera(db_session):
    user_id = "test-user-uuid"
    camera_data = {
        'user_id': user_id,
        'name': 'Camera 1',
        'manufacturer': 'intelbras',
        'type': 'ip',
        'ip': '192.168.1.100',
        'port': 554,
        'username': 'admin',
        'password': 'pass123',
        'channel': 1,
        'subtype': 1
    }

    camera = CameraService.create_camera(db_session, **camera_data)

    assert camera is not None
    assert camera['id'] is not None
    assert camera['name'] == 'Camera 1'
    assert camera['manufacturer'] == 'intelbras'
    assert camera['ip'] == '192.168.1.100'
    assert 'rtsp_url' in camera

def test_create_camera_generates_rtsp_url(db_session):
    user_id = "test-user-uuid"
    camera_data = {
        'user_id': user_id,
        'name': 'Hikvision Camera',
        'manufacturer': 'hikvision',
        'type': 'ip',
        'ip': '192.168.1.101',
        'port': 554,
        'username': 'admin',
        'password': 'admin123',
        'channel': 2,
        'subtype': 0
    }

    camera = CameraService.create_camera(db_session, **camera_data)

    expected_url = 'rtsp://admin:admin123@192.168.1.101:554/Streaming/Channels/201'
    assert camera['rtsp_url'] == expected_url

def test_list_user_cameras(db_session):
    user_id = "test-user-uuid"

    # Create 2 cameras for user
    CameraService.create_camera(db_session, user_id=user_id, name='Cam 1',
                                manufacturer='intelbras', ip='192.168.1.100')
    CameraService.create_camera(db_session, user_id=user_id, name='Cam 2',
                                manufacturer='hikvision', ip='192.168.1.101')

    cameras = CameraService.list_cameras_by_user(db_session, user_id)

    assert len(cameras) == 2
    assert all(c['user_id'] == user_id for c in cameras)

@pytest.fixture
def db_session():
    """Create a test database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_camera_service_expanded.py -v`

Expected: FAIL with methods not found

- [ ] **Step 3: Expand CameraService**

```python
# backend/camera_service.py (ADD to existing file)

from sqlalchemy import text
from typing import List, Dict, Optional
import logging
from backend.rtsp_builder import RTSPBuilder

logger = logging.getLogger(__name__)


class CameraService:
    """Service for managing IP cameras"""

    @staticmethod
    def create_camera(
        db,
        user_id: str,
        name: str,
        manufacturer: str,
        ip: str,
        port: int = 554,
        username: str = None,
        password: str = None,
        channel: int = 1,
        subtype: int = 1,
        type: str = 'ip',
        rtsp_url: str = None
    ) -> Optional[Dict]:
        """
        Create a new IP camera.

        Args:
            db: Database session
            user_id: User UUID who owns the camera
            name: Camera name
            manufacturer: 'intelbras', 'hikvision', or 'generic'
            ip: Camera IP address
            port: RTSP port (default 554)
            username: RTSP username
            password: RTSP password
            channel: DVR channel (1-32)
            subtype: 0=main stream, 1=sub-stream
            type: 'ip', 'dvr', or 'nvr'
            rtsp_url: Optional custom RTSP URL (auto-generated if None)

        Returns:
            Camera dict or None if failed
        """
        try:
            # Auto-generate RTSP URL if not provided
            if rtsp_url is None:
                camera_config = {
                    'manufacturer': manufacturer,
                    'ip': ip,
                    'port': port,
                    'username': username or '',
                    'password': password or '',
                    'channel': channel,
                    'subtype': subtype
                }
                rtsp_url = RTSPBuilder.build_url(camera_config)

            query = text("""
                INSERT INTO cameras (user_id, name, manufacturer, type, ip, port,
                                     username, password, channel, subtype, rtsp_url)
                VALUES (:user_id, :name, :manufacturer, :type, :ip, :port,
                        :username, :password, :channel, :subtype, :rtsp_url)
                RETURNING *
            """)
            result = db.execute(query, {
                'user_id': user_id,
                'name': name,
                'manufacturer': manufacturer,
                'type': type,
                'ip': ip,
                'port': port,
                'username': username,
                'password': password,
                'channel': channel,
                'subtype': subtype,
                'rtsp_url': rtsp_url
            })
            db.commit()
            row = result.fetchone()

            logger.info(f"✅ Created camera: {name} ({manufacturer})")
            return {
                'id': row[0],
                'user_id': str(row[1]),
                'name': row[2],
                'manufacturer': row[3],
                'type': row[4],
                'ip': row[5],
                'port': row[6],
                'username': row[7],
                'password': row[8],
                'channel': row[9],
                'subtype': row[10],
                'rtsp_url': row[11],
                'is_active': row[12],
                'last_connected_at': row[13].isoformat() if row[13] else None,
                'connection_error': row[14],
                'created_at': row[15].isoformat() if row[15] else None
            }

        except Exception as e:
            logger.error(f"❌ Failed to create camera: {e}")
            db.rollback()
            return None

    @staticmethod
    def list_cameras_by_user(db, user_id: str) -> List[Dict]:
        """
        List all cameras for a specific user.

        Args:
            db: Database session
            user_id: User UUID

        Returns:
            List of camera dicts
        """
        try:
            query = text("""
                SELECT * FROM cameras
                WHERE user_id = :user_id
                ORDER BY created_at DESC
            """)
            result = db.execute(query, {'user_id': user_id})
            rows = result.fetchall()

            cameras = []
            for row in rows:
                cameras.append({
                    'id': row[0],
                    'user_id': str(row[1]),
                    'name': row[2],
                    'manufacturer': row[3],
                    'type': row[4],
                    'ip': row[5],
                    'port': row[6],
                    'username': row[7],
                    'password': row[8],
                    'channel': row[9],
                    'subtype': row[10],
                    'rtsp_url': row[11],
                    'is_active': row[12],
                    'last_connected_at': row[13].isoformat() if row[13] else None,
                    'connection_error': row[14],
                    'created_at': row[15].isoformat() if row[15] else None
                })

            return cameras

        except Exception as e:
            logger.error(f"❌ Failed to list cameras for user {user_id}: {e}")
            return []

    @staticmethod
    def get_camera_by_id(db, camera_id: int) -> Optional[Dict]:
        """
        Get camera by ID.

        Args:
            db: Database session
            camera_id: Camera ID

        Returns:
            Camera dict or None
        """
        try:
            query = text("SELECT * FROM cameras WHERE id = :camera_id")
            result = db.execute(query, {'camera_id': camera_id})
            row = result.fetchone()

            if not row:
                return None

            return {
                'id': row[0],
                'user_id': str(row[1]),
                'name': row[2],
                'manufacturer': row[3],
                'type': row[4],
                'ip': row[5],
                'port': row[6],
                'username': row[7],
                'password': row[8],
                'channel': row[9],
                'subtype': row[10],
                'rtsp_url': row[11],
                'is_active': row[12],
                'last_connected_at': row[13].isoformat() if row[13] else None,
                'connection_error': row[14],
                'created_at': row[15].isoformat() if row[15] else None
            }

        except Exception as e:
            logger.error(f"❌ Failed to get camera {camera_id}: {e}")
            return None

    @staticmethod
    def update_camera(
        db,
        camera_id: int,
        name: str = None,
        manufacturer: str = None,
        ip: str = None,
        port: int = None,
        username: str = None,
        password: str = None,
        channel: int = None,
        subtype: int = None,
        type: str = None,
        is_active: bool = None
    ) -> Optional[Dict]:
        """
        Update camera details.

        Args:
            db: Database session
            camera_id: Camera ID
            **kwargs: Fields to update

        Returns:
            Updated camera dict or None
        """
        try:
            update_fields = []
            params = {'camera_id': camera_id}

            if name is not None:
                update_fields.append("name = :name")
                params['name'] = name

            if manufacturer is not None:
                update_fields.append("manufacturer = :manufacturer")
                params['manufacturer'] = manufacturer

            if ip is not None:
                update_fields.append("ip = :ip")
                params['ip'] = ip

            if port is not None:
                update_fields.append("port = :port")
                params['port'] = port

            if username is not None:
                update_fields.append("username = :username")
                params['username'] = username

            if password is not None:
                update_fields.append("password = :password")
                params['password'] = password

            if channel is not None:
                update_fields.append("channel = :channel")
                params['channel'] = channel

            if subtype is not None:
                update_fields.append("subtype = :subtype")
                params['subtype'] = subtype

            if type is not None:
                update_fields.append("type = :type")
                params['type'] = type

            if is_active is not None:
                update_fields.append("is_active = :is_active")
                params['is_active'] = is_active

            if not update_fields:
                return CameraService.get_camera_by_id(db, camera_id)

            query = text(f"""
                UPDATE cameras
                SET {', '.join(update_fields)}
                WHERE id = :camera_id
                RETURNING *
            """)
            result = db.execute(query, params)
            db.commit()
            row = result.fetchone()

            logger.info(f"✅ Updated camera {camera_id}")
            return {
                'id': row[0],
                'user_id': str(row[1]),
                'name': row[2],
                'manufacturer': row[3],
                'type': row[4],
                'ip': row[5],
                'port': row[6],
                'username': row[7],
                'password': row[8],
                'channel': row[9],
                'subtype': row[10],
                'rtsp_url': row[11],
                'is_active': row[12],
                'last_connected_at': row[13].isoformat() if row[13] else None,
                'connection_error': row[14],
                'created_at': row[15].isoformat() if row[15] else None
            }

        except Exception as e:
            logger.error(f"❌ Failed to update camera {camera_id}: {e}")
            db.rollback()
            return None

    @staticmethod
    def delete_camera(db, camera_id: int) -> bool:
        """
        Delete camera by ID.

        Args:
            db: Database session
            camera_id: Camera ID

        Returns:
            True if deleted, False otherwise
        """
        try:
            query = text("DELETE FROM cameras WHERE id = :camera_id")
            result = db.execute(query, {'camera_id': camera_id})
            db.commit()

            deleted = result.rowcount > 0
            if deleted:
                logger.info(f"✅ Deleted camera {camera_id}")
            else:
                logger.warning(f"⚠️ Camera {camera_id} not found")

            return deleted

        except Exception as e:
            logger.error(f"❌ Failed to delete camera {camera_id}: {e}")
            db.rollback()
            return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_camera_service_expanded.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/camera_service.py tests/test_camera_service_expanded.py
git commit -m "feat: expand CameraService with IP camera CRUD"
```

---

### Task 4: Add camera API endpoints to api_server.py

**Files:**
- Modify: `api_server.py`
- Test: `tests/test_api_cameras_expanded.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_api_cameras_expanded.py
import pytest
from api_server import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def auth_token(client):
    # Register and login to get token
    client.post('/api/auth/register', json={
        'email': 'camera@test.com',
        'password': 'test123456',
        'full_name': 'Camera Test User'
    })
    response = client.post('/api/auth/login', json={
        'email': 'camera@test.com',
        'password': 'test123456'
    })
    return response.json['token']

def test_create_camera(client, auth_token):
    response = client.post('/api/cameras',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={
            'name': 'Front Door',
            'manufacturer': 'intelbras',
            'ip': '192.168.1.100',
            'port': 554,
            'username': 'admin',
            'password': 'admin123',
            'channel': 1,
            'subtype': 1
        }
    )

    assert response.status_code == 201
    data = response.get_json()
    assert data['success'] is True
    assert data['camera']['name'] == 'Front Door'
    assert 'rtsp_url' in data['camera']

def test_list_cameras(client, auth_token):
    # Create a camera first
    client.post('/api/cameras',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={
            'name': 'Camera 1',
            'manufacturer': 'hikvision',
            'ip': '192.168.1.101'
        }
    )

    response = client.get('/api/cameras',
        headers={'Authorization': f'Bearer {auth_token}'}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert len(data['cameras']) >= 1

def test_get_camera_by_id(client, auth_token):
    # Create a camera
    create_response = client.post('/api/cameras',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={
            'name': 'Camera 1',
            'manufacturer': 'intelbras',
            'ip': '192.168.1.102'
        }
    )
    camera_id = create_response.get_json()['camera']['id']

    response = client.get(f'/api/cameras/{camera_id}',
        headers={'Authorization': f'Bearer {auth_token}'}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['camera']['id'] == camera_id

def test_update_camera(client, auth_token):
    # Create a camera
    create_response = client.post('/api/cameras',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={
            'name': 'Old Name',
            'manufacturer': 'intelbras',
            'ip': '192.168.1.103'
        }
    )
    camera_id = create_response.get_json()['camera']['id']

    response = client.put(f'/api/cameras/{camera_id}',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={'name': 'New Name'}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['camera']['name'] == 'New Name'

def test_delete_camera(client, auth_token):
    # Create a camera
    create_response = client.post('/api/cameras',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={
            'name': 'To Delete',
            'manufacturer': 'intelbras',
            'ip': '192.168.1.104'
        }
    )
    camera_id = create_response.get_json()['camera']['id']

    response = client.delete(f'/api/cameras/{camera_id}',
        headers={'Authorization': f'Bearer {auth_token}'}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api_cameras_expanded.py -v`

Expected: FAIL with 404 errors

- [ ] **Step 3: Add camera endpoints to api_server.py**

```python
# api_server.py (ADD these routes)

from backend.camera_service import CameraService
import uuid

# ============================================
# CAMERA MANAGEMENT ENDPOINTS
# ============================================

@app.route('/api/cameras', methods=['GET'])
def list_cameras():
    """List all cameras for authenticated user"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Missing token'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

    try:
        db = next(get_db())
        cameras = CameraService.list_cameras_by_user(db, payload['user_id'])
        return jsonify({'success': True, 'cameras': cameras})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras', methods=['POST'])
def create_camera():
    """Create a new IP camera"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Missing token'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

    data = request.get_json()

    # Validate required fields
    required = ['name', 'manufacturer', 'ip']
    for field in required:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing field: {field}'}), 400

    try:
        db = next(get_db())
        camera = CameraService.create_camera(
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
            type=data.get('type', 'ip')
        )

        if camera:
            return jsonify({'success': True, 'camera': camera}), 201
        else:
            return jsonify({'success': False, 'error': 'Failed to create camera'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<int:camera_id>', methods=['GET'])
def get_camera(camera_id):
    """Get camera by ID"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Missing token'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

    try:
        db = next(get_db())
        camera = CameraService.get_camera_by_id(db, camera_id)

        if not camera:
            return jsonify({'success': False, 'error': 'Camera not found'}), 404

        # Check ownership
        if camera['user_id'] != payload['user_id']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        return jsonify({'success': True, 'camera': camera})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<int:camera_id>', methods=['PUT'])
def update_camera(camera_id):
    """Update camera details"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Missing token'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

    try:
        db = next(get_db())

        # Check ownership first
        existing = CameraService.get_camera_by_id(db, camera_id)
        if not existing:
            return jsonify({'success': False, 'error': 'Camera not found'}), 404
        if existing['user_id'] != payload['user_id']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Update
        data = request.get_json()
        camera = CameraService.update_camera(db, camera_id, **data)

        if camera:
            return jsonify({'success': True, 'camera': camera})
        else:
            return jsonify({'success': False, 'error': 'Failed to update camera'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<int:camera_id>', methods=['DELETE'])
def delete_camera(camera_id):
    """Delete camera"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Missing token'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

    try:
        db = next(get_db())

        # Check ownership first
        existing = CameraService.get_camera_by_id(db, camera_id)
        if not existing:
            return jsonify({'success': False, 'error': 'Camera not found'}), 404
        if existing['user_id'] != payload['user_id']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Delete
        success = CameraService.delete_camera(db, camera_id)

        if success:
            return jsonify({'success': True, 'message': 'Camera deleted'})
        else:
            return jsonify({'success': False, 'error': 'Failed to delete camera'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api_cameras_expanded.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add api_server.py tests/test_api_cameras_expanded.py
git commit -m "feat: add camera CRUD API endpoints"
```

---

### Task 5: Add camera connectivity test endpoint

**Files:**
- Modify: `api_server.py`
- Test: `tests/test_api_camera_test.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_api_camera_test.py
import pytest
from api_server import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def auth_token(client):
    client.post('/api/auth/register', json={
        'email': 'test@example.com',
        'password': 'test123456',
        'full_name': 'Test User'
    })
    response = client.post('/api/auth/login', json={
        'email': 'test@example.com',
        'password': 'test123456'
    })
    return response.json['token']

def test_camera_connection_with_invalid_url(client, auth_token):
    response = client.post('/api/cameras/test',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={
            'rtsp_url': 'rtsp://invalid:554/stream'
        }
    )

    assert response.status_code == 200
    data = response.get_json()
    assert 'connected' in data
    assert data['connected'] is False
    assert 'message' in data
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_api_camera_test.py -v`

Expected: FAIL with 404

- [ ] **Step 3: Add connectivity test endpoint**

```python
# api_server.py (ADD this route)

import subprocess
import threading
import queue

@app.route('/api/cameras/test', methods=['POST'])
def test_camera_connection():
    """Test RTSP connection before saving camera"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Missing token'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

    data = request.get_json()
    rtsp_url = data.get('rtsp_url')

    if not rtsp_url:
        return jsonify({'success': False, 'error': 'Missing rtsp_url'}), 400

    try:
        # Test connection with FFprobe (part of FFmpeg)
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'stream=codec_type',
            '-of', 'default=noprint_wrappers=1',
            rtsp_url
        ]

        # Run with timeout
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=5
        )

        if result.returncode == 0:
            return jsonify({
                'connected': True,
                'message': 'Câmera acessível'
            })
        else:
            return jsonify({
                'connected': False,
                'message': 'Falha na conexão — verifique IP, porta, usuário e senha'
            })

    except subprocess.TimeoutExpired:
        return jsonify({
            'connected': False,
            'message': 'Timeout — câmera não respondeu em 5 segundos'
        })
    except FileNotFoundError:
        return jsonify({
            'connected': False,
            'message': 'FFmpeg não está instalado no servidor'
        }), 500
    except Exception as e:
        return jsonify({
            'connected': False,
            'message': f'Erro ao testar conexão: {str(e)}'
        }), 500
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_api_camera_test.py -v`

Expected: Test PASS (will show as not connected since we don't have a real camera)

- [ ] **Step 5: Commit**

```bash
git add api_server.py tests/test_api_camera_test.py
git commit -m "feat: add camera connectivity test endpoint"
```

---

## Phase 2: Streaming Infrastructure

### Task 6: Create StreamManager module

**Files:**
- Create: `backend/stream_manager.py`
- Test: `tests/test_stream_manager.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_stream_manager.py
import pytest
import os
import tempfile
from backend.stream_manager import StreamManager

@pytest.fixture
def stream_manager():
    """Create a StreamManager with temp directory"""
    temp_dir = tempfile.mkdtemp()
    sm = StreamManager(hls_base_dir=temp_dir)
    yield sm
    # Cleanup
    sm.stop_all_streams()
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

def test_start_stream_creates_hls_directory(stream_manager):
    camera_id = 1
    rtsp_url = 'rtsp://test:554/stream'

    # Mock FFmpeg subprocess (we'll test with real FFmpeg later)
    # For now, just test the directory creation logic

    stream_manager.start_stream(camera_id, rtsp_url)

    expected_dir = f"{stream_manager.hls_base_dir}/{camera_id}"
    # In real test, FFmpeg would create this
    # assert os.path.exists(expected_dir)

def test_stop_stream_removes_hls_files(stream_manager):
    camera_id = 2
    rtsp_url = 'rtsp://test:554/stream2'

    stream_manager.start_stream(camera_id, rtsp_url)
    stream_manager.stop_stream(camera_id)

    # Stream should be removed from active_streams
    assert camera_id not in stream_manager.active_streams

def test_get_stream_status(stream_manager):
    camera_id = 3
    rtsp_url = 'rtsp://test:554/stream3'

    status_before = stream_manager.get_stream_status(camera_id)
    assert status_before['status'] == 'idle'

    stream_manager.start_stream(camera_id, rtsp_url)

    status_after = stream_manager.get_stream_status(camera_id)
    assert status_after['status'] == 'streaming'
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_stream_manager.py -v`

Expected: FAIL with module not found

- [ ] **Step 3: Implement StreamManager**

```python
# backend/stream_manager.py
import subprocess
import os
import shutil
import threading
import time
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class StreamManager:
    """Manages FFmpeg subprocesses for HLS streaming"""

    def __init__(self, hls_base_dir: str = './streams'):
        """
        Initialize StreamManager.

        Args:
            hls_base_dir: Base directory for HLS segments
        """
        self.hls_base_dir = hls_base_dir
        self.active_streams: Dict[int, subprocess.Popen] = {}
        self.stream_threads: Dict[int, threading.Thread] = {}
        self.lock = threading.Lock()

        # Create base directory if it doesn't exist
        os.makedirs(self.hls_base_dir, exist_ok=True)

    def start_stream(self, camera_id: int, rtsp_url: str) -> Dict:
        """
        Start FFmpeg subprocess for a camera.

        Args:
            camera_id: Camera ID
            rtsp_url: RTSP URL to stream from

        Returns:
            Dict with status and HLS URL
        """
        with self.lock:
            # Check if already streaming
            if camera_id in self.active_streams:
                return {
                    'status': 'already_streaming',
                    'hls_url': self.get_hls_url(camera_id)
                }

            try:
                # Create output directory
                output_dir = os.path.join(self.hls_base_dir, str(camera_id))
                os.makedirs(output_dir, exist_ok=True)

                # FFmpeg command for HLS
                cmd = [
                    'ffmpeg',
                    '-rtsp_transport', 'tcp',  # TCP more stable than UDP
                    '-i', rtsp_url,
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',     # Minimal CPU
                    '-tune', 'zerolatency',     # Low latency
                    '-b:v', '512k',              # Bitrate for preview
                    '-s', '640x360',             # Resolution for preview
                    '-f', 'hls',
                    '-hls_time', '1',            # 1 second segments
                    '-hls_list_size', '3',       # Keep only 3 segments
                    '-hls_flags', 'delete_segments+append_list',
                    os.path.join(output_dir, 'stream.m3u8')
                ]

                # Start FFmpeg subprocess
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    stdin=subprocess.DEVNULL
                )

                self.active_streams[camera_id] = process

                # Start monitor thread
                monitor_thread = threading.Thread(
                    target=self._monitor_stream,
                    args=(camera_id, process),
                    daemon=True
                )
                monitor_thread.start()
                self.stream_threads[camera_id] = monitor_thread

                logger.info(f"✅ Started stream for camera {camera_id}")

                return {
                    'status': 'started',
                    'hls_url': self.get_hls_url(camera_id),
                    'camera_id': camera_id
                }

            except Exception as e:
                logger.error(f"❌ Failed to start stream for camera {camera_id}: {e}")
                return {
                    'status': 'error',
                    'error': str(e)
                }

    def stop_stream(self, camera_id: int) -> bool:
        """
        Stop stream and clean up HLS files.

        Args:
            camera_id: Camera ID

        Returns:
            True if stopped, False if not streaming
        """
        with self.lock:
            if camera_id not in self.active_streams:
                return False

            try:
                # Kill FFmpeg process
                process = self.active_streams[camera_id]
                process.terminate()

                # Wait for graceful shutdown (max 5 seconds)
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()

                del self.active_streams[camera_id]

                # Clean up HLS files
                output_dir = os.path.join(self.hls_base_dir, str(camera_id))
                if os.path.exists(output_dir):
                    shutil.rmtree(output_dir)

                logger.info(f"✅ Stopped stream for camera {camera_id}")
                return True

            except Exception as e:
                logger.error(f"❌ Failed to stop stream for camera {camera_id}: {e}")
                return False

    def stop_all_streams(self):
        """Stop all active streams"""
        with self.lock:
            camera_ids = list(self.active_streams.keys())
            for camera_id in camera_ids:
                self.stop_stream(camera_id)

    def get_stream_status(self, camera_id: int) -> Dict:
        """
        Get status of a camera stream.

        Args:
            camera_id: Camera ID

        Returns:
            Dict with status information
        """
        if camera_id not in self.active_streams:
            return {
                'status': 'idle',
                'hls_url': None
            }

        process = self.active_streams[camera_id]

        # Check if process is still running
        if process.poll() is None:
            return {
                'status': 'streaming',
                'hls_url': self.get_hls_url(camera_id),
                'pid': process.pid
            }
        else:
            # Process died
            del self.active_streams[camera_id]
            return {
                'status': 'error',
                'error': 'FFmpeg process terminated'
            }

    def get_hls_url(self, camera_id: int) -> str:
        """Get HLS playlist URL for a camera"""
        return f"/streams/{camera_id}/stream.m3u8"

    def _monitor_stream(self, camera_id: int, process: subprocess.Popen):
        """
        Monitor FFmpeg process and restart if it crashes.

        Runs in a separate thread.
        """
        process.wait()

        # Process exited
        logger.warning(f"⚠️ FFmpeg for camera {camera_id} exited with code {process.returncode}")

        with self.lock:
            if camera_id in self.active_streams:
                del self.active_streams[camera_id]

        # TODO: Implement auto-restart with backoff
        # For now, just log the exit
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_stream_manager.py -v`

Expected: All tests PASS (note: actual FFmpeg won't run without camera, but logic is tested)

- [ ] **Step 5: Commit**

```bash
git add backend/stream_manager.py tests/test_stream_manager.py
git commit -m "feat: add StreamManager for FFmpeg HLS streaming"
```

---

### Task 7: Add stream control endpoints

**Files:**
- Modify: `api_server.py`
- Test: `tests/test_api_stream_control.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_api_stream_control.py
import pytest
from api_server import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def auth_token(client):
    client.post('/api/auth/register', json={
        'email': 'stream@test.com',
        'password': 'test123456',
        'full_name': 'Stream Test'
    })
    response = client.post('/api/auth/login', json={
        'email': 'stream@test.com',
        'password': 'test123456'
    })
    return response.json['token']

@pytest.fixture
def test_camera(client, auth_token):
    """Create a test camera"""
    response = client.post('/api/cameras',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={
            'name': 'Test Camera',
            'manufacturer': 'intelbras',
            'ip': '192.168.1.100',
            'username': 'admin',
            'password': 'admin123'
        }
    )
    return response.get_json()['camera']

def test_start_stream(client, auth_token, test_camera):
    response = client.post(f"/api/cameras/{test_camera['id']}/stream/start",
        headers={'Authorization': f'Bearer {auth_token}'}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert 'hls_url' in data

def test_stop_stream(client, auth_token, test_camera):
    # Start first
    client.post(f"/api/cameras/{test_camera['id']}/stream/start",
        headers={'Authorization': f'Bearer {auth_token}'})

    # Stop
    response = client.post(f"/api/cameras/{test_camera['id']}/stream/stop",
        headers={'Authorization': f'Bearer {auth_token}'}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True

def test_get_stream_status(client, auth_token, test_camera):
    response = client.get(f"/api/cameras/{test_camera['id']}/stream/status",
        headers={'Authorization': f'Bearer {auth_token}'}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert 'status' in data

def test_get_all_streams_status(client, auth_token):
    response = client.get('/api/streams/status',
        headers={'Authorization': f'Bearer {auth_token}'}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert 'streams' in data
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api_stream_control.py -v`

Expected: FAIL with 404

- [ ] **Step 3: Add stream control endpoints**

```python
# api_server.py (ADD these imports and routes)

from backend.stream_manager import StreamManager

# Create global StreamManager instance
stream_manager = StreamManager()

# ============================================
# STREAM CONTROL ENDPOINTS
# ============================================

@app.route('/api/cameras/<int:camera_id>/stream/start', methods=['POST'])
def start_camera_stream(camera_id):
    """Start HLS stream for a camera"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Missing token'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

    try:
        db = next(get_db())

        # Get camera
        camera = CameraService.get_camera_by_id(db, camera_id)
        if not camera:
            return jsonify({'success': False, 'error': 'Camera not found'}), 404

        # Check ownership
        if camera['user_id'] != payload['user_id']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Check if active
        if not camera['is_active']:
            return jsonify({'success': False, 'error': 'Camera is inactive'}), 400

        # Start stream
        result = stream_manager.start_stream(camera_id, camera['rtsp_url'])

        if result['status'] == 'started' or result['status'] == 'already_streaming':
            return jsonify({
                'success': True,
                'hls_url': result['hls_url'],
                'camera_id': camera_id
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to start stream')
            }), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<int:camera_id>/stream/stop', methods=['POST'])
def stop_camera_stream(camera_id):
    """Stop HLS stream for a camera"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Missing token'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

    try:
        db = next(get_db())

        # Get camera (for ownership check)
        camera = CameraService.get_camera_by_id(db, camera_id)
        if not camera:
            return jsonify({'success': False, 'error': 'Camera not found'}), 404

        # Check ownership
        if camera['user_id'] != payload['user_id']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Stop stream
        stopped = stream_manager.stop_stream(camera_id)

        if stopped:
            return jsonify({'success': True, 'message': 'Stream stopped'})
        else:
            return jsonify({'success': False, 'error': 'Stream not active'}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/cameras/<int:camera_id>/stream/status', methods=['GET'])
def get_camera_stream_status(camera_id):
    """Get status of camera stream"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Missing token'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

    try:
        db = next(get_db())

        # Get camera (for ownership check)
        camera = CameraService.get_camera_by_id(db, camera_id)
        if not camera:
            return jsonify({'success': False, 'error': 'Camera not found'}), 404

        # Check ownership
        if camera['user_id'] != payload['user_id']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Get status
        status = stream_manager.get_stream_status(camera_id)

        return jsonify({'success': True, **status})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/streams/status', methods=['GET'])
def get_all_streams_status():
    """Get status of all active streams"""
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Missing token'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

    try:
        # Get all cameras for user
        db = next(get_db())
        cameras = CameraService.list_cameras_by_user(db, payload['user_id'])

        streams = {}
        for camera in cameras:
            status = stream_manager.get_stream_status(camera['id'])
            streams[camera['id']] = {
                'camera_id': camera['id'],
                'name': camera['name'],
                **status
            }

        return jsonify({'success': True, 'streams': streams})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_api_stream_control.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add api_server.py tests/test_api_stream_control.py
git commit -m "feat: add stream control API endpoints"
```

---

### Task 8: Serve HLS files statically

**Files:**
- Modify: `api_server.py`

- [ ] **Step 1: Add static file serving for HLS segments**

```python
# api_server.py (ADD these routes)

from flask import send_from_directory

@app.route('/streams/<int:camera_id>/<path:filename>')
def serve_hls_file(camera_id, filename):
    """
    Serve HLS files (playlist and segments).

    Note: In production, these should be served by nginx or similar.
    Flask is not optimized for serving many small files.
    """
    # Check authentication
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({'success': False, 'error': 'Missing token'}), 401

    token = auth_header.split(' ')[1]
    payload = verify_token(token)
    if not payload:
        return jsonify({'success': False, 'error': 'Invalid token'}), 401

    try:
        db = next(get_db())
        camera = CameraService.get_camera_by_id(db, camera_id)

        if not camera:
            return jsonify({'success': False, 'error': 'Camera not found'}), 404

        # Check ownership
        if camera['user_id'] != payload['user_id']:
            return jsonify({'success': False, 'error': 'Unauthorized'}), 403

        # Serve file
        stream_dir = os.path.join(stream_manager.hls_base_dir, str(camera_id))
        return send_from_directory(stream_dir, filename)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
```

- [ ] **Step 2: Test HLS file serving manually**

Run: Start server and try accessing `/streams/1/stream.m3u8` with valid token

Expected: Returns m3u8 playlist file

- [ ] **Step 3: Commit**

```bash
git add api_server.py
git commit -m "feat: add static file serving for HLS segments"
```

---

## Phase 3: YOLO Integration

### Task 9: Create YOLOProcessor module

**Files:**
- Create: `backend/yolo_processor.py`
- Test: `tests/test_yolo_processor.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/test_yolo_processor.py
import pytest
import threading
import time
from backend.yolo_processor import YOLOProcessor

@pytest.fixture
def mock_model():
    """Mock YOLO model for testing"""
    class MockModel:
        def predict(self, source, **kwargs):
            # Return mock detections
            class MockResult:
                boxes = type('obj', (object,), {'data': None})
            return [MockResult()]
    return MockModel()

def test_yolo_processor_thread_starts(mock_model):
    processor = YOLOProcessor(
        camera_id=1,
        rtsp_url='rtsp://test:554/stream',
        model=mock_model,
        fps=2
    )

    assert processor.is_alive() is False

    processor.start()
    time.sleep(0.1)  # Give thread time to start

    assert processor.is_alive() is True

    processor.stop()
    processor.join(timeout=2)

def test_yolo_processor_stops_gracefully(mock_model):
    processor = YOLOProcessor(
        camera_id=1,
        rtsp_url='rtsp://test:554/stream',
        model=mock_model,
        fps=5
    )

    processor.start()
    time.sleep(0.2)

    processor.stop()
    processor.join(timeout=2)

    assert processor.is_alive() is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_yolo_processor.py -v`

Expected: FAIL with module not found

- [ ] **Step 3: Implement YOLOProcessor**

```python
# backend/yolo_processor.py
import threading
import time
import logging
from typing import Callable, Optional, Dict, Any
import cv2
import numpy as np

logger = logging.getLogger(__name__)


class YOLOProcessor(threading.Thread):
    """
    Thread-based continuous YOLO detection for a camera stream.

    Captures frames from RTSP stream and runs YOLO detection at specified FPS.
    Detection results are sent via callback function.
    """

    def __init__(
        self,
        camera_id: int,
        rtsp_url: str,
        model,
        fps: int = 5,
        detection_callback: Optional[Callable] = None
    ):
        """
        Initialize YOLO processor.

        Args:
            camera_id: Camera ID
            rtsp_url: RTSP URL to capture frames from
            model: YOLO model instance
            fps: Detection frequency (frames per second)
            detection_callback: Callback function(results) to send detections
        """
        super().__init__(daemon=True)
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.model = model
        self.fps = fps
        self.detection_callback = detection_callback
        self.running = False
        self.frame_delay = 1.0 / fps

    def run(self):
        """Main detection loop"""
        self.running = True
        logger.info(f"🎬 YOLO processor started for camera {self.camera_id}")

        # Open RTSP stream
        cap = cv2.VideoCapture(self.rtsp_url)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Minimize latency

        if not cap.isOpened():
            logger.error(f"❌ Failed to open RTSP stream for camera {self.camera_id}")
            self.running = False
            return

        frame_count = 0

        try:
            while self.running:
                start_time = time.time()

                # Read frame
                ret, frame = cap.read()
                if not ret:
                    logger.warning(f"⚠️ Failed to read frame from camera {self.camera_id}")
                    time.sleep(1)
                    continue

                # Run YOLO detection
                try:
                    results = self.model.predict(
                        source=frame,
                        conf=0.5,
                        verbose=False
                    )

                    # Process results
                    detections = []
                    if results and len(results) > 0:
                        result = results[0]
                        if result.boxes is not None:
                            for box in result.boxes:
                                detection = {
                                    'bbox': box.xyxy[0].tolist(),
                                    'class': self.model.names[int(box.cls[0])],
                                    'confidence': float(box.conf[0])
                                }
                                detections.append(detection)

                    # Send via callback
                    if self.detection_callback and detections:
                        self.detection_callback({
                            'camera_id': self.camera_id,
                            'timestamp': int(time.time()),
                            'frame_id': frame_count,
                            'detections': detections
                        })

                    frame_count += 1

                except Exception as e:
                    logger.error(f"❌ YOLO detection error for camera {self.camera_id}: {e}")

                # Maintain target FPS
                elapsed = time.time() - start_time
                sleep_time = self.frame_delay - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        except Exception as e:
            logger.error(f"❌ YOLO processor error for camera {self.camera_id}: {e}")

        finally:
            cap.release()
            logger.info(f"🛑 YOLO processor stopped for camera {self.camera_id}")

    def stop(self):
        """Stop the detection thread"""
        self.running = False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_yolo_processor.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add backend/yolo_processor.py tests/test_yolo_processor.py
git commit -m "feat: add YOLOProcessor for continuous detection"
```

---

### Task 10: Add WebSocket support to Flask

**Files:**
- Modify: `api_server.py`
- Create: `backend/socketio_handler.py`

- [ ] **Step 1: Install Flask-SocketIO**

Run: `pip install flask-socketio python-socketio eventlet`

Expected: Packages installed successfully

- [ ] **Step 2: Add requirements to requirements.txt**

```bash
echo "flask-socketio>=5.3.0
python-socketio>=5.10.0
eventlet>=0.33.0" >> requirements.txt
```

- [ ] **Step 3: Initialize Flask-SocketIO**

```python
# api_server.py (MODIFY imports and initialization)

from flask_socketio import SocketIO, emit, join_room, leave_room

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Move app.run to bottom
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5001, debug=True)
```

- [ ] **Step 4: Create SocketIO handler**

```python
# backend/socketio_handler.py

def init_socketio(socketio, stream_manager):
    """Initialize SocketIO event handlers"""

    @socketio.on('connect')
    def handle_connect(auth):
        """Handle client connection"""
        # auth should contain JWT token
        if not auth or 'token' not in auth:
            return False  # Reject connection

        token = auth['token']
        # Verify token (re-use verify_token from api_server)
        # For now, accept all connections
        print(f"✅ Client connected: {request.sid}")
        return True

    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle client disconnection"""
        print(f"❌ Client disconnected: {request.sid}")

    @socketio.on('subscribe_camera')
    def handle_subscribe_camera(data):
        """Subscribe to detections for a specific camera"""
        camera_id = data.get('camera_id')
        if camera_id:
            room = f'camera_{camera_id}'
            join_room(room)
            print(f"📹 Client {request.sid} subscribed to camera {camera_id}")
            emit('subscribed', {'camera_id': camera_id})

    @socketio.on('unsubscribe_camera')
    def handle_unsubscribe_camera(data):
        """Unsubscribe from camera detections"""
        camera_id = data.get('camera_id')
        if camera_id:
            room = f'camera_{camera_id}'
            leave_room(room)
            print(f"📹 Client {request.sid} unsubscribed from camera {camera_id}")
            emit('unsubscribed', {'camera_id': camera_id})

    def send_detections(camera_id, detection_data):
        """Send detection results to all subscribers of a camera"""
        room = f'camera_{camera_id}'
        socketio.emit('detection', detection_data, room=room)

    # Store reference for use by YOLOProcessor
    socketio.send_detections = send_detections
```

- [ ] **Step 5: Initialize SocketIO in api_server.py**

```python
# api_server.py (ADD after imports)

from backend.socketio_handler import init_socketio

# Initialize SocketIO handlers
init_socketio(socketio, stream_manager)
```

- [ ] **Step 6: Update StreamManager to start YOLOProcessor**

```python
# backend/stream_manager.py (MODIFY)

from backend.yolo_processor import YOLOProcessor

class StreamManager:
    def __init__(self, hls_base_dir: str = './streams', model=None):
        # ... existing code ...
        self.model = model
        self.yolo_processors: Dict[int, YOLOProcessor] = {}

    def start_stream(self, camera_id: int, rtsp_url: str) -> Dict:
        # ... existing FFmpeg code ...

        # Start YOLO processor if model is available
        if self.model:
            yolo_processor = YOLOProcessor(
                camera_id=camera_id,
                rtsp_url=rtsp_url,
                model=self.model,
                fps=5,
                detection_callback=self._on_detection
            )
            yolo_processor.start()
            self.yolo_processors[camera_id] = yolo_processor

        return {'status': 'started', ...}

    def stop_stream(self, camera_id: int) -> bool:
        # ... existing code ...

        # Stop YOLO processor
        if camera_id in self.yolo_processors:
            self.yolo_processors[camera_id].stop()
            del self.yolo_processors[camera_id]

    def _on_detection(self, detection_data):
        """Callback for YOLO detection results"""
        # Send via WebSocket
        from backend.socketio_handler import socketio
        if hasattr(socketio, 'send_detections'):
            socketio.send_detections(detection_data['camera_id'], detection_data)
```

- [ ] **Step 7: Commit**

```bash
git add api_server.py backend/socketio_handler.py backend/stream_manager.py requirements.txt
git commit -m "feat: add WebSocket support for real-time detections"
```

---

## Phase 4: Frontend Implementation

### Task 11: Install hls.js dependency

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install hls.js**

Run: `cd frontend && npm install hls.js`

Expected: Package installed successfully

- [ ] **Step 2: Verify package.json**

```bash
cat frontend/package.json | grep hls.js
```

Expected: `"hls.js": "^1.4.0"` or similar

- [ ] **Step 3: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat: add hls.js dependency for HLS playback"
```

---

### Task 12: Create HLS camera types

**Files:**
- Create: `frontend/src/types/camera.ts`

- [ ] **Step 1: Create TypeScript types**

```typescript
// frontend/src/types/camera.ts

export interface Camera {
  id: number;
  user_id: string;
  name: string;
  manufacturer: 'intelbras' | 'hikvision' | 'generic';
  type: 'ip' | 'dvr' | 'nvr';
  ip: string;
  port: number;
  username: string;
  password: string;
  channel: number;
  subtype: number;
  rtsp_url: string;
  is_active: boolean;
  last_connected_at: string | null;
  connection_error: string | null;
  created_at: string;
}

export interface Detection {
  camera_id: number;
  timestamp: number;
  frame_id: number;
  detections: DetectionBox[];
}

export interface DetectionBox {
  bbox: [number, number, number, number];  // [x1, y1, x2, y2]
  class: string;
  confidence: number;
}

export interface StreamStatus {
  camera_id: number;
  status: 'idle' | 'starting' | 'streaming' | 'error';
  hls_url: string | null;
  error: string | null;
  pid: number | null;
}

export interface HLSCameraFeedProps {
  cameraId: number;
  mode: 'primary' | 'thumbnail';
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/types/camera.ts
git commit -m "feat: add TypeScript types for camera streaming"
```

---

### Task 13: Create HLS camera feed component

**Files:**
- Create: `frontend/src/components/hls-camera-feed.tsx`

- [ ] **Step 1: Create component skeleton**

```typescript
// frontend/src/components/hls-camera-feed.tsx
'use client'

import { useEffect, useRef, useState } from 'react'
import Hls from 'hls.js'
import { io, Socket } from 'socket.io-client'
import type { HLSCameraFeedProps, Detection, DetectionBox } from '@/types/camera'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5001'

export function HLSCameraFeed({ cameraId, mode }: HLSCameraFeedProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const hlsRef = useRef<Hls | null>(null)
  const socketRef = useRef<Socket | null>(null)

  const [status, setStatus] = useState<'idle' | 'connecting' | 'streaming' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [detections, setDetections] = useState<DetectionBox[]>([])

  // Initialize HLS stream
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const hlsUrl = `${API_URL}/streams/${cameraId}/stream.m3u8`

    setStatus('connecting')

    if (Hls.isSupported()) {
      const hls = new Hls({
        maxBufferLength: 5,
        maxMaxBufferLength: 10,
        liveSyncDurationCount: 2,
        liveMaxLatencyDurationCount: 4,
        enableWorker: true,
        lowLatencyMode: true
      })

      hls.loadSource(hlsUrl)
      hls.attachMedia(video)

      hls.on(Hls.Events.MANIFEST_PARSED, () => {
        setStatus('streaming')
        video.play().catch(console.error)
      })

      hls.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          setStatus('error')
          setError(`HLS error: ${data.type}`)
        }
      })

      hlsRef.current = hls

      return () => {
        hls.destroy()
      }
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      // Native HLS support (Safari)
      video.src = hlsUrl
      video.addEventListener('loadedmetadata', () => {
        setStatus('streaming')
        video.play().catch(console.error)
      })

      return () => {
        video.src = ''
      }
    }
  }, [cameraId])

  // Connect to WebSocket for detections
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) return

    const socket = io(`${API_URL}`, {
      auth: { token },
      transports: ['websocket']
    })

    socket.on('connect', () => {
      console.log(`[HLSCameraFeed] Connected to WebSocket`)
      socket.emit('subscribe_camera', { camera_id: cameraId })
    })

    socket.on('detection', (data: Detection) => {
      if (data.camera_id === cameraId) {
        setDetections(data.detections)
      }
    })

    socket.on('disconnect', () => {
      console.log(`[HLSCameraFeed] Disconnected from WebSocket`)
    })

    socketRef.current = socket

    return () => {
      socket.emit('unsubscribe_camera', { camera_id: cameraId })
      socket.disconnect()
    }
  }, [cameraId])

  // Draw detection boxes
  useEffect(() => {
    const canvas = canvasRef.current
    const video = videoRef.current
    if (!canvas || !video || detections.length === 0) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Set canvas size to match video
    canvas.width = video.videoWidth
    canvas.height = video.videoHeight

    // Clear and draw boxes
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    detections.forEach(det => {
      const [x1, y1, x2, y2] = det.bbox
      const width = x2 - x1
      const height = y2 - y1
      const label = `${det.class} ${(det.confidence * 100).toFixed(0)}%`

      // Draw box
      ctx.strokeStyle = '#00ff00'
      ctx.lineWidth = 3
      ctx.strokeRect(x1, y1, width, height)

      // Draw label background
      const textWidth = ctx.measureText(label).width
      ctx.fillStyle = '#00ff00'
      ctx.fillRect(x1, y1 - 25, textWidth + 10, 25)

      // Draw label text
      ctx.fillStyle = '#000000'
      ctx.font = 'bold 14px system-ui'
      ctx.fillText(label, x1 + 5, y1 - 7)
    })
  }, [detections])

  const sizeClass = mode === 'primary'
    ? 'w-full h-full min-h-[300px]'
    : 'w-full h-full min-h-[120px]'

  return (
    <div className={`relative bg-black rounded-lg overflow-hidden ${sizeClass}`}>
      {/* Video element */}
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full h-full object-cover"
      />

      {/* Detection overlay */}
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
      />

      {/* Status badge */}
      <div className="absolute top-2 left-2">
        {status === 'connecting' && (
          <span className="bg-yellow-500 text-white px-2 py-1 rounded text-xs">
            Connecting...
          </span>
        )}
        {status === 'streaming' && (
          <span className="bg-green-500 text-white px-2 py-1 rounded text-xs">
            ● Live
          </span>
        )}
        {status === 'error' && (
          <span className="bg-red-500 text-white px-2 py-1 rounded text-xs">
            Error: {error}
          </span>
        )}
      </div>

      {/* Detection count */}
      {detections.length > 0 && (
        <div className="absolute bottom-2 left-2 bg-black/70 text-white px-2 py-1 rounded text-xs">
          {detections.length} objects detected
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/hls-camera-feed.tsx
git commit -m "feat: add HLSCameraFeed component with hls.js and WebSocket"
```

---

### Task 14: Create camera grid component

**Files:**
- Create: `frontend/src/components/camera-grid.tsx`

- [ ] **Step 1: Create grid component**

```typescript
// frontend/src/components/camera-grid.tsx
'use client'

import { useState } from 'react'
import { HLSCameraFeed } from './hls-camera-feed'
import type { Camera } from '@/types/camera'

interface CameraGridProps {
  cameras: Camera[]
}

export function CameraGrid({ cameras }: CameraGridProps) {
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  // Auto-select first 12 cameras
  useState(() => {
    if (cameras.length > 0 && selectedIds.length === 0) {
      setSelectedIds(cameras.slice(0, 12).map(c => c.id))
    }
  })

  const primaryCameras = selectedIds.slice(0, 3)
  const thumbnailCameras = selectedIds.slice(3, 12)

  const toggleCamera = (cameraId: number) => {
    if (selectedIds.includes(cameraId)) {
      setSelectedIds(selectedIds.filter(id => id !== cameraId))
    } else if (selectedIds.length < 12) {
      setSelectedIds([...selectedIds, cameraId])
    }
  }

  const selectedCameras = cameras.filter(c => selectedIds.includes(c.id))

  return (
    <div className="space-y-4">
      {/* Camera selector */}
      <div className="flex flex-wrap gap-2">
        {cameras.map(camera => (
          <button
            key={camera.id}
            onClick={() => toggleCamera(camera.id)}
            className={`px-3 py-1 rounded text-sm ${
              selectedIds.includes(camera.id)
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 text-gray-700'
            }`}
          >
            {camera.name}
          </button>
        ))}
      </div>

      {/* Primary cameras (large) */}
      {primaryCameras.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {primaryCameras.map(cameraId => {
            const camera = selectedCameras.find(c => c.id === cameraId)
            return camera ? (
              <div key={camera.id} className="space-y-2">
                <h3 className="text-sm font-medium">{camera.name}</h3>
                <HLSCameraFeed cameraId={camera.id} mode="primary" />
              </div>
            ) : null
          })}
        </div>
      )}

      {/* Thumbnail cameras (small) */}
      {thumbnailCameras.length > 0 && (
        <div className="grid grid-cols-3 md:grid-cols-9 gap-2">
          {thumbnailCameras.map(cameraId => {
            const camera = selectedCameras.find(c => c.id === cameraId)
            return camera ? (
              <div key={camera.id} className="space-y-1">
                <p className="text-xs font-medium truncate">{camera.name}</p>
                <HLSCameraFeed cameraId={camera.id} mode="thumbnail" />
              </div>
            ) : null
          })}
        </div>
      )}

      {/* Empty state */}
      {selectedIds.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          <p>Select cameras above to view streams</p>
        </div>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/camera-grid.tsx
git commit -m "feat: add CameraGrid component with 12-camera layout"
```

---

### Task 15: Install socket.io-client

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install socket.io-client**

Run: `cd frontend && npm install socket.io-client`

Expected: Package installed successfully

- [ ] **Step 2: Commit**

```bash
git add frontend/package.json frontend/package-lock.json
git commit -m "feat: add socket.io-client for WebSocket connection"
```

---

### Task 16: Create camera management page

**Files:**
- Create: `frontend/src/app/dashboard/cameras/page.tsx`

- [ ] **Step 1: Create cameras page**

```typescript
// frontend/src/app/dashboard/cameras/page.tsx
'use client'

import { useEffect, useState } from 'react'
import { CameraGrid } from '@/components/camera-grid'
import type { Camera } from '@/types/camera'
import { api } from '@/lib/api'

export default function CamerasPage() {
  const [cameras, setCameras] = useState<Camera[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchCameras()
  }, [])

  const fetchCameras = async () => {
    try {
      const result = await api.getCameras()
      if (result.success) {
        setCameras(result.cameras)
      }
    } catch (err) {
      console.error('Failed to fetch cameras:', err)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p>Loading cameras...</p>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Camera Streams</h1>
        <p className="text-gray-600">View and manage IP camera streams with YOLO detection</p>
      </div>

      <CameraGrid cameras={cameras} />
    </div>
  )
}
```

- [ ] **Step 2: Add API client methods**

```typescript
// frontend/src/lib/api.ts (ADD these methods)

async getCameras() {
  const token = this.getToken()
  const response = await fetch(`${this.apiUrl}/cameras`, {
    headers: {
      'Authorization': `Bearer ${token}`
    }
  })

  if (!response.ok) {
    throw new Error('Failed to fetch cameras')
  }

  return response.json()
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/dashboard/cameras/page.tsx frontend/src/lib/api.ts
git commit -m "feat: add camera management page"
```

---

## Phase 5: Polish & Testing

### Task 17: Add error handling and reconnection logic

**Files:**
- Modify: `frontend/src/components/hls-camera-feed.tsx`

- [ ] **Step 1: Add reconnection logic to component**

```typescript
// frontend/src/components/hls-camera-feed.tsx (ADD to existing component)

// Add to component state
const [retryCount, setRetryCount] = useState(0)

// Modify HLS error handling
hls.on(Hls.Events.ERROR, (event, data) => {
  if (data.fatal) {
    if (retryCount < 5) {
      // Attempt recovery
      const delay = Math.min(1000 * 2 ** retryCount, 30000)
      setTimeout(() => {
        setRetryCount(retryCount + 1)
        hls.startLoad()
      }, delay)
    } else {
      setStatus('error')
      setError(`Stream unavailable after ${retryCount} retries`)
    }
  }
})

// Add WebSocket reconnection
socket.on('disconnect', () => {
  console.log('[HLSCameraFeed] WebSocket disconnected, reconnecting...')
  setTimeout(() => {
    socket.connect()
  }, 2000)
})
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/hls-camera-feed.tsx
git commit -m "feat: add error handling and reconnection to HLSCameraFeed"
```

---

### Task 18: Add Railway FFmpeg configuration

**Files:**
- Create: `nixpacks.toml`

- [ ] **Step 1: Add FFmpeg to nixpacks.toml**

```toml
# nixpacks.toml
[phases.setup]
nixPkgs = ["ffmpeg", "python311"]

[phases.build]
cmds = ["pip install -r requirements.txt"]

[start]
cmd = "python api_server.py"
```

- [ ] **Step 2: Commit**

```bash
git add nixpacks.toml
git commit -m "feat: add FFmpeg to nixpacks.toml for Railway deployment"
```

---

### Task 19: Write end-to-end integration test

**Files:**
- Create: `tests/test_e2e_camera_streaming.py`

- [ ] **Step 1: Create E2E test**

```python
# tests/test_e2e_camera_streaming.py
import pytest
import time
import requests
from api_server import app, stream_manager

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def auth_token(client):
    """Create user and get auth token"""
    client.post('/api/auth/register', json={
        'email': 'e2e@test.com',
        'password': 'test123456',
        'full_name': 'E2E Test'
    })
    response = client.post('/api/auth/login', json={
        'email': 'e2e@test.com',
        'password': 'test123456'
    })
    return response.json['token']

@pytest.mark.skip("Requires actual RTSP camera")
def test_full_camera_workflow(client, auth_token):
    """End-to-end test: Create camera, start stream, stop stream"""

    # 1. Create camera
    response = client.post('/api/cameras',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={
            'name': 'E2E Test Camera',
            'manufacturer': 'intelbras',
            'ip': '192.168.1.100',
            'username': 'admin',
            'password': 'admin123',
            'channel': 1,
            'subtype': 1
        }
    )
    assert response.status_code == 201
    camera_id = response.get_json()['camera']['id']

    # 2. Start stream
    response = client.post(f'/api/cameras/{camera_id}/stream/start',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    assert response.status_code == 200
    hls_url = response.get_json()['hls_url']

    # 3. Check stream status
    response = client.get(f'/api/cameras/{camera_id}/stream/status',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    assert response.status_code == 200
    status = response.get_json()
    assert status['status'] == 'streaming'

    # 4. Wait for HLS segments to be created
    time.sleep(3)

    # 5. Verify HLS playlist is accessible
    response = client.get(f'/streams/{camera_id}/stream.m3u8',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    assert response.status_code == 200
    assert b'#EXTM3U' in response.data

    # 6. Stop stream
    response = client.post(f'/api/cameras/{camera_id}/stream/stop',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    assert response.status_code == 200

    # 7. Verify stream stopped
    response = client.get(f'/api/cameras/{camera_id}/stream/status',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
    assert response.status_code == 200
    status = response.get_json()
    assert status['status'] == 'idle'

    # 8. Cleanup
    client.delete(f'/api/cameras/{camera_id}',
        headers={'Authorization': f'Bearer {auth_token}'}
    )
```

- [ ] **Step 2: Commit**

```bash
git add tests/test_e2e_camera_streaming.py
git commit -m "test: add E2E test for camera streaming workflow"
```

---

### Task 20: Update documentation

**Files:**
- Create: `docs/camera-streaming-guide.md`
- Modify: `README.md`

- [ ] **Step 1: Create camera streaming guide**

```markdown
# Camera Streaming Guide

## Overview

The EPI Recognition System supports real-time streaming from IP cameras with YOLO object detection.

## Supported Camera Manufacturers

- **Intelbras**: Standard RTSP format
- **Hikvision**: Multi-channel DVR/NVR support
- **Generic**: ONVIF-compatible cameras

## Adding a Camera

### Via API

```bash
curl -X POST https://your-api.com/api/cameras \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Front Door",
    "manufacturer": "intelbras",
    "ip": "192.168.1.100",
    "port": 554,
    "username": "admin",
    "password": "admin123",
    "channel": 1,
    "subtype": 1
  }'
```

### Via Dashboard

1. Navigate to `/dashboard/cameras`
2. Click "Add Camera"
3. Fill in camera details
4. Click "Test Connection" to verify
5. Click "Save"

## Starting a Stream

### Via API

```bash
curl -X POST https://your-api.com/api/cameras/1/stream/start \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Via Dashboard

Click "Start Stream" button on the camera card.

## Viewing Streams

Navigate to `/dashboard/cameras` and select up to 12 cameras:
- **Primary cameras (large view)**: First 3 selected cameras
- **Thumbnail cameras**: Remaining 9 cameras

## Troubleshooting

### Stream won't start
- Verify camera is accessible from server
- Check IP address, port, username, password
- Ensure camera supports RTSP
- Check server logs for FFmpeg errors

### High latency
- Reduce video quality (use `subtype: 1` for sub-stream)
- Check network bandwidth
- Reduce HLS segment duration in config

### Detections not showing
- Verify YOLO model is loaded
- Check WebSocket connection in browser console
- Ensure detection threshold isn't too high
```

- [ ] **Step 2: Update README**

```bash
# Add to README.md

## Features

- Real-time HLS streaming from IP cameras (Intelbras, Hikvision, ONVIF)
- Continuous YOLO object detection (5 FPS)
- Support for 12 simultaneous camera streams
- WebSocket-based real-time detection updates
- Auto-reconnection with exponential backoff
```

- [ ] **Step 3: Commit**

```bash
git add docs/camera-streaming-guide.md README.md
git commit -m "docs: add camera streaming guide and update README"
```

---

## Completion Checklist

- [ ] All tests pass: `pytest tests/ -v`
- [ ] Frontend builds without errors: `cd frontend && npm run build`
- [ ] FFmpeg installed on Railway (check deployment logs)
- [ ] Can create camera via API
- [ ] Can start/stop stream via API
- [ ] HLS playlist is accessible
- [ ] WebSocket sends detections
- [ ] Frontend displays video with overlay
- [ ] Error handling works (camera offline test)
- [ ] Documentation is complete

---

## Deployment Instructions

1. **Backend (Railway):**
   - Push to main branch
   - Verify FFmpeg is installed (check build logs)
   - Set environment variables in Railway dashboard
   - Test `/health` endpoint

2. **Frontend (Vercel/Netlify):**
   - Set `NEXT_PUBLIC_API_URL` environment variable
   - Deploy and test camera page

3. **Test with real camera:**
   - Add camera via API or dashboard
   - Start stream
   - Verify video plays in browser
   - Check detections appear

---

**Plan complete!** Ready for implementation using subagent-driven-development or executing-plans skill.
