"""
Integration tests for YOLO Training API endpoints.

Tests the complete flow:
1. Create project
2. Start training
3. Check training status
4. Activate model
"""
import pytest
import uuid
from api_server import app
from sqlalchemy import text


@pytest.fixture(scope="function")
def client():
    """Create test client."""
    app.config['TESTING'] = True

    # Create test user
    with app.test_client() as client:
        # Register user
        response = client.post('/api/auth/register', json={
            'email': f'test-training-{uuid.uuid4().hex[:8]}@example.com',
            'password': 'test123456',
            'full_name': 'Test Training User',
            'company_name': 'Test Company'
        })

        if response.status_code == 201:
            token = response.json['token']
        else:
            # Login if user exists
            response = client.post('/api/auth/login', json={
                'email': response.json.get('email', 'test@example.com'),
                'password': 'test123456'
            })
            token = response.json['token']

        headers = {'Authorization': f'Bearer {token}'}
        yield client, headers


@pytest.fixture(scope="function")
def test_project(client):
    """Create a test training project."""
    client, headers = client

    response = client.post('/api/training/projects', headers=headers, json={
        'name': 'Test Training Project',
        'description': 'Project for testing training execution',
        'target_classes': ['helmet', 'vest']
    })

    assert response.status_code == 201
    return response.json['project']['id']


def test_start_training_endpoint(client, test_project):
    """Test starting training via API endpoint."""
    client, headers = client

    config = {
        'epochs': 10,
        'batch_size': 8,
        'image_size': 640,
        'device': 'cpu'
    }

    augmentation = {
        'hsv_h': 0.015,
        'hsv_s': 0.7,
        'fliplr': 0.5
    }

    response = client.post(
        f'/api/training/projects/{test_project}/train',
        headers=headers,
        json={
            'config': config,
            'augmentation': augmentation,
            'model': 'yolov8n.pt'
        }
    )

    assert response.status_code == 200
    data = response.json
    assert data['success'] is True
    assert 'training_id' in data
    print(f"✅ Training started: {data['training_id']}")


def test_get_training_status_endpoint(client, test_project):
    """Test getting training status via API endpoint."""
    client, headers = client

    # Start training first
    config = {'epochs': 10, 'batch_size': 8, 'device': 'cpu'}
    client.post(
        f'/api/training/projects/{test_project}/train',
        headers=headers,
        json={'config': config}
    )

    # Get status
    response = client.get(
        f'/api/training/projects/{test_project}/training-status',
        headers=headers
    )

    assert response.status_code == 200
    data = response.json
    assert data['success'] is True
    assert 'status' in data
    assert data['status'] in ['not_started', 'running', 'completed', 'failed']
    print(f"✅ Training status: {data['status']}")


def test_activate_model_endpoint(client, test_project):
    """Test activating a trained model via API endpoint."""
    client, headers = client

    # First, we need to create a trained model in the database
    from backend.database import get_db

    db = next(get_db())
    try:
        # Create a dummy trained model
        model_id = str(uuid.uuid4())

        query = text("""
            INSERT INTO trained_models
            (id, project_id, model_name, version, storage_path,
             map50, precision, recall, is_active, created_at)
            VALUES (:id, :project_id, :model_name, 1, :storage_path,
                    0.85, 0.88, 0.82, false, NOW())
        """)

        db.execute(query, {
            'id': model_id,
            'project_id': test_project,
            'model_name': 'test_model',
            'storage_path': 'models/test.pt'
        })
        db.commit()
    finally:
        db.close()

    # Activate the model
    response = client.post(
        f'/api/training/models/{model_id}/activate',
        headers=headers
    )

    assert response.status_code == 200
    data = response.json
    assert data['success'] is True
    print(f"✅ Model activated: {data['message']}")


def test_training_unauthorized(client):
    """Test that training endpoints require authentication."""
    client, _ = client

    response = client.post(
        f'/api/training/projects/{uuid.uuid4()}/train',
        json={'config': {'epochs': 10}}
    )

    assert response.status_code == 401
    assert 'error' in response.json


def test_training_unauthorized_status(client):
    """Test that status endpoint requires authentication."""
    client, _ = client

    response = client.get(
        f'/api/training/projects/{uuid.uuid4()}/training-status'
    )

    assert response.status_code == 401


def test_activate_model_unauthorized(client):
    """Test that activate endpoint requires authentication."""
    client, _ = client

    response = client.post(
        f'/api/training/models/{uuid.uuid4()}/activate'
    )

    assert response.status_code == 401
