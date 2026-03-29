"""
Tests for training projects API endpoints.

This test suite validates the REST API endpoints for training project CRUD operations.
"""
import pytest
import uuid
from api_server import app


@pytest.fixture
def client():
    """Create test client with authenticated user."""
    app.config['TESTING'] = True

    with app.test_client() as client:
        # Create test user and get token
        response = client.post('/api/auth/register', json={
            'email': f'training-test-{uuid.uuid4()}@local.dev',
            'password': '123456',
            'full_name': 'Training Test',
            'company_name': 'Test Company'
        })

        assert response.status_code in [200, 201], f"Failed to setup test user: {response.data}"
        token = response.json['token']
        headers = {'Authorization': f'Bearer {token}'}
        yield client, headers


def test_create_training_project(client):
    """Test creating a training project via API."""
    client, headers = client

    response = client.post('/api/training/projects', headers=headers, json={
        'name': 'EPI Detection',
        'description': 'Detect safety equipment',
        'target_classes': ['helmet', 'vest', 'gloves']
    })

    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.data}"
    data = response.json
    assert data['success'] is True
    assert data['project']['name'] == 'EPI Detection'
    assert data['project']['target_classes'] == ['helmet', 'vest', 'gloves']
    assert 'id' in data['project']
    assert data['project']['status'] == 'draft'


def test_create_training_project_missing_name(client):
    """Test creating project without name fails."""
    client, headers = client

    response = client.post('/api/training/projects', headers=headers, json={
        'description': 'No name',
        'target_classes': ['helmet']
    })

    assert response.status_code == 400
    data = response.json
    assert data['success'] is False
    assert 'name' in data['error'].lower()


def test_create_training_project_missing_target_classes(client):
    """Test creating project without target classes fails."""
    client, headers = client

    response = client.post('/api/training/projects', headers=headers, json={
        'name': 'Test Project',
        'description': 'No target classes'
    })

    assert response.status_code == 400
    data = response.json
    assert data['success'] is False
    assert 'target' in data['error'].lower()


def test_create_training_project_invalid_target_classes_type(client):
    """Test that target_classes must be an array, not a string."""
    client, headers = client

    response = client.post('/api/training/projects', headers=headers, json={
        'name': 'Test Project',
        'target_classes': 'helmet'  # String instead of array
    })

    assert response.status_code == 400
    data = response.json
    assert data['success'] is False
    assert 'array' in data['error'].lower()


def test_create_training_project_unauthorized():
    """Test creating project without authentication fails."""
    app.config['TESTING'] = True

    with app.test_client() as client:
        response = client.post('/api/training/projects', json={
            'name': 'Unauthorized Project',
            'target_classes': ['helmet']
        })

        assert response.status_code == 401


def test_list_training_projects(client):
    """Test listing all training projects for current user."""
    client, headers = client

    # Create multiple projects
    client.post('/api/training/projects', headers=headers, json={
        'name': 'Project 1',
        'target_classes': ['helmet']
    })

    client.post('/api/training/projects', headers=headers, json={
        'name': 'Project 2',
        'target_classes': ['vest']
    })

    # List projects
    response = client.get('/api/training/projects', headers=headers)

    assert response.status_code == 200
    data = response.json
    assert data['success'] is True
    assert len(data['projects']) >= 2
    project_names = [p['name'] for p in data['projects']]
    assert 'Project 1' in project_names
    assert 'Project 2' in project_names


def test_get_training_project_by_id(client):
    """Test retrieving a specific training project."""
    client, headers = client

    # Create project
    create_response = client.post('/api/training/projects', headers=headers, json={
        'name': 'Get Test Project',
        'target_classes': ['helmet', 'vest']
    })

    project_id = create_response.json['project']['id']

    # Get project
    response = client.get(f'/api/training/projects/{project_id}', headers=headers)

    assert response.status_code == 200
    data = response.json
    assert data['success'] is True
    assert data['project']['id'] == project_id
    assert data['project']['name'] == 'Get Test Project'


def test_get_training_project_not_found(client):
    """Test retrieving non-existent project returns 404."""
    client, headers = client

    fake_id = str(uuid.uuid4())
    response = client.get(f'/api/training/projects/{fake_id}', headers=headers)

    assert response.status_code == 404
    data = response.json
    assert data['success'] is False
    assert 'not found' in data['error'].lower()


def test_update_training_project(client):
    """Test updating a training project."""
    client, headers = client

    # Create project
    create_response = client.post('/api/training/projects', headers=headers, json={
        'name': 'Original Name',
        'description': 'Original description',
        'target_classes': ['helmet']
    })

    project_id = create_response.json['project']['id']

    # Update project
    response = client.put(f'/api/training/projects/{project_id}', headers=headers, json={
        'name': 'Updated Name',
        'description': 'Updated description',
        'target_classes': ['helmet', 'vest', 'gloves']
    })

    assert response.status_code == 200
    data = response.json
    assert data['success'] is True
    assert data['project']['name'] == 'Updated Name'
    assert data['project']['description'] == 'Updated description'
    assert data['project']['target_classes'] == ['helmet', 'vest', 'gloves']


def test_update_training_project_partial(client):
    """Test partial update of training project."""
    client, headers = client

    # Create project
    create_response = client.post('/api/training/projects', headers=headers, json={
        'name': 'Partial Update Test',
        'description': 'Original description',
        'target_classes': ['helmet']
    })

    project_id = create_response.json['project']['id']

    # Update only name
    response = client.put(f'/api/training/projects/{project_id}', headers=headers, json={
        'name': 'New Name Only'
    })

    assert response.status_code == 200
    data = response.json
    assert data['project']['name'] == 'New Name Only'
    assert data['project']['description'] == 'Original description'  # Unchanged
    assert data['project']['target_classes'] == ['helmet']  # Unchanged


def test_delete_training_project(client):
    """Test deleting a training project."""
    client, headers = client

    # Create project
    create_response = client.post('/api/training/projects', headers=headers, json={
        'name': 'To Delete',
        'target_classes': ['helmet']
    })

    project_id = create_response.json['project']['id']

    # Delete project
    response = client.delete(f'/api/training/projects/{project_id}', headers=headers)

    assert response.status_code == 200
    data = response.json
    assert data['success'] is True
    assert 'deleted' in data['message'].lower()

    # Verify deletion
    get_response = client.get(f'/api/training/projects/{project_id}', headers=headers)
    assert get_response.status_code == 404


def test_update_project_status(client):
    """Test updating project status via PATCH endpoint."""
    client, headers = client

    # Create project
    create_response = client.post('/api/training/projects', headers=headers, json={
        'name': 'Status Test',
        'target_classes': ['helmet']
    })

    project_id = create_response.json['project']['id']
    assert create_response.json['project']['status'] == 'draft'

    # Update status to in_progress
    response = client.patch(f'/api/training/projects/{project_id}/status', headers=headers, json={
        'status': 'in_progress'
    })

    assert response.status_code == 200
    data = response.json
    assert data['success'] is True
    assert data['project']['status'] == 'in_progress'

    # Update status to completed
    response = client.patch(f'/api/training/projects/{project_id}/status', headers=headers, json={
        'status': 'completed'
    })

    assert response.status_code == 200
    assert response.json['project']['status'] == 'completed'


def test_update_project_status_missing_status(client):
    """Test that status update requires status field."""
    client, headers = client

    # Create project
    create_response = client.post('/api/training/projects', headers=headers, json={
        'name': 'Status Validation Test',
        'target_classes': ['helmet']
    })

    project_id = create_response.json['project']['id']

    # Try to update without status field
    response = client.patch(f'/api/training/projects/{project_id}/status', headers=headers, json={})

    assert response.status_code == 400
    data = response.json
    assert data['success'] is False
    assert 'status' in data['error'].lower()


def test_update_project_status_invalid_value(client):
    """Test that invalid status values are rejected."""
    client, headers = client

    # Create project
    create_response = client.post('/api/training/projects', headers=headers, json={
        'name': 'Invalid Status Test',
        'target_classes': ['helmet']
    })

    project_id = create_response.json['project']['id']

    # Try invalid status
    response = client.patch(f'/api/training/projects/{project_id}/status', headers=headers, json={
        'status': 'invalid_status_value'
    })

    assert response.status_code == 400
    data = response.json
    assert data['success'] is False
