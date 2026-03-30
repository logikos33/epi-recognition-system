# tests/test_api_annotations.py
"""
Tests for annotation API endpoints.
"""
import pytest
import uuid
from sqlalchemy import text
from api_server import app
from backend.database import get_db


@pytest.fixture
def client():
    """Create test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Try to login first, if fails register new user
        import uuid
        unique_email = f'annotation-test-{uuid.uuid4()}@local.dev'

        response = client.post('/api/auth/register', json={
            'email': unique_email,
            'password': '123456',
            'full_name': 'Annotation Test'
        })
        token = response.json['token']
        headers = {'Authorization': f'Bearer {token}'}
        yield client, headers


@pytest.fixture
def test_project(client):
    """Create test project with video, frame, and annotations."""
    client, headers = client

    # Create project
    response = client.post('/api/training/projects', headers=headers, json={
        'name': 'Annotation Test Project',
        'description': 'Test annotation endpoints',
        'target_classes': ['helmet', 'vest', 'gloves']
    })
    project_id = response.json['project']['id']

    # Create video
    response = client.post('/api/training/videos', headers=headers, data={
        'project_id': project_id,
        'video': (open('/dev/null', 'rb'), 'test.mp4')
    })
    # Note: This will fail without actual video file, so we'll insert directly

    # Insert video and frame directly
    db = next(get_db())

    video_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO training_videos (id, project_id, filename, storage_path, duration_seconds, frame_count, fps)
        VALUES (:video_id, :project_id, :filename, :storage_path, 10.0, 10, 30.0)
    """), {
        'video_id': video_id,
        'project_id': project_id,
        'filename': 'test.mp4',
        'storage_path': '/tmp/test.mp4'
    })

    frame_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO training_frames (id, video_id, frame_number, storage_path)
        VALUES (:frame_id, :video_id, 0, :storage_path)
    """), {
        'frame_id': frame_id,
        'video_id': video_id,
        'storage_path': '/tmp/frame_000000.jpg'
    })
    db.commit()
    db.close()

    return {'project_id': project_id, 'frame_id': frame_id}


def test_create_annotation(client, test_project):
    """Test creating an annotation via API"""
    client, headers = client
    frame_id = test_project['frame_id']

    response = client.post('/api/training/annotations', headers=headers, json={
        'frame_id': frame_id,
        'class_name': 'helmet',
        'bbox_x': 100.0,
        'bbox_y': 200.0,
        'bbox_width': 50.0,
        'bbox_height': 60.0
    })

    assert response.status_code == 201
    data = response.json
    assert data['success'] is True
    assert data['annotation']['class_name'] == 'helmet'
    assert data['annotation']['bbox_x'] == 100.0


def test_get_frame_annotations(client, test_project):
    """Test getting annotations for a frame"""
    client, headers = client
    frame_id = test_project['frame_id']

    # Create multiple annotations
    client.post('/api/training/annotations', headers=headers, json={
        'frame_id': frame_id,
        'class_name': 'helmet',
        'bbox_x': 100.0,
        'bbox_y': 200.0,
        'bbox_width': 50.0,
        'bbox_height': 60.0
    })

    client.post('/api/training/annotations', headers=headers, json={
        'frame_id': frame_id,
        'class_name': 'vest',
        'bbox_x': 300.0,
        'bbox_y': 400.0,
        'bbox_width': 80.0,
        'bbox_height': 100.0
    })

    # Get annotations
    response = client.get(f'/api/training/frames/{frame_id}/annotations', headers=headers)

    assert response.status_code == 200
    data = response.json
    assert data['success'] is True
    assert len(data['annotations']) == 2


def test_update_annotation(client, test_project):
    """Test updating an annotation"""
    client, headers = client
    frame_id = test_project['frame_id']

    # Create annotation
    create_response = client.post('/api/training/annotations', headers=headers, json={
        'frame_id': frame_id,
        'class_name': 'helmet',
        'bbox_x': 100.0,
        'bbox_y': 200.0,
        'bbox_width': 50.0,
        'bbox_height': 60.0
    })
    annotation_id = create_response.json['annotation']['id']

    # Update annotation
    response = client.put(f'/api/training/annotations/{annotation_id}', headers=headers, json={
        'bbox_x': 150.0,
        'bbox_y': 250.0,
        'bbox_width': 55.0,
        'bbox_height': 65.0
    })

    assert response.status_code == 200
    assert response.json['success'] is True


def test_delete_annotation(client, test_project):
    """Test deleting an annotation"""
    client, headers = client
    frame_id = test_project['frame_id']

    # Create annotation
    create_response = client.post('/api/training/annotations', headers=headers, json={
        'frame_id': frame_id,
        'class_name': 'helmet',
        'bbox_x': 100.0,
        'bbox_y': 200.0,
        'bbox_width': 50.0,
        'bbox_height': 60.0
    })
    annotation_id = create_response.json['annotation']['id']

    # Delete annotation
    response = client.delete(f'/api/training/annotations/{annotation_id}', headers=headers)

    assert response.status_code == 200
    assert response.json['success'] is True

    # Verify deletion
    get_response = client.get(f'/api/training/frames/{frame_id}/annotations', headers=headers)
    assert len(get_response.json['annotations']) == 0
