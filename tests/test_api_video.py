"""
Tests for video upload API endpoints.

This test suite validates the REST API endpoints for video upload,
listing, getting, and deleting training videos.
"""
import pytest
import os
import tempfile
import uuid
import base64
from api_server import app


@pytest.fixture(scope="function")
def client():
    """Create a test client."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture(scope="function")
def test_user(client):
    """Create a test user and return auth token."""
    # Register user
    unique_id = str(uuid.uuid4())[:8]
    response = client.post('/api/auth/register', json={
        'email': f'video_test_{unique_id}@local.dev',
        'password': '123456',
        'full_name': 'Video Test User',
        'company_name': 'Test Company'
    })

    assert response.status_code == 201
    data = response.get_json()
    token = data['token']

    return {
        'token': token,
        'user_id': data['user']['id']
    }


@pytest.fixture(scope="function")
def test_project(client, test_user):
    """Create a test training project."""
    headers = {'Authorization': f'Bearer {test_user["token"]}'}

    response = client.post('/api/training/projects', headers=headers, json={
        'name': 'Test Project for Videos',
        'description': 'Test project for video API testing',
        'target_classes': ['helmet', 'vest']
    })

    assert response.status_code == 201
    data = response.get_json()
    return data['project']


def test_upload_video_no_file(client, test_user, test_project):
    """Test upload endpoint rejects request without file."""
    headers = {'Authorization': f'Bearer {test_user["token"]}'}

    response = client.post('/api/training/videos', headers=headers, data={
        'project_id': test_project['id']
    })

    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'No video file provided' in data['error']


def test_upload_video_no_project_id(client, test_user):
    """Test upload endpoint rejects request without project_id."""
    headers = {'Authorization': f'Bearer {test_user["token"]}'}

    # Create a dummy file
    data = {
        'video': (tempfile.NamedTemporaryFile(suffix='.mp4'), 'test.mp4')
    }

    response = client.post('/api/training/videos', headers=headers, data=data, content_type='multipart/form-data')

    assert response.status_code == 400
    data = response.get_json()
    assert data['success'] is False
    assert 'project_id is required' in data['error']


def test_list_project_videos_empty(client, test_user, test_project):
    """Test listing videos when project has no videos."""
    headers = {'Authorization': f'Bearer {test_user["token"]}'}

    response = client.get(f'/api/training/projects/{test_project["id"]}/videos', headers=headers)

    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
    assert data['videos'] == []
    assert data['count'] == 0


def test_get_video_not_found(client, test_user):
    """Test getting non-existent video."""
    headers = {'Authorization': f'Bearer {test_user["token"]}'}

    fake_video_id = str(uuid.uuid4())
    response = client.get(f'/api/training/videos/{fake_video_id}', headers=headers)

    assert response.status_code == 404
    data = response.get_json()
    assert data['success'] is False


def test_delete_video_not_found(client, test_user):
    """Test deleting non-existent video."""
    headers = {'Authorization': f'Bearer {test_user["token"]}'}

    fake_video_id = str(uuid.uuid4())
    response = client.delete(f'/api/training/videos/{fake_video_id}', headers=headers)

    assert response.status_code == 404
    data = response.get_json()
    assert data['success'] is False


def test_unauthorized_access(client):
    """Test that endpoints require authentication."""
    # Try to list videos without token
    response = client.get('/api/training/projects/fake-id/videos')

    assert response.status_code == 401
    data = response.get_json()
    assert data['success'] is False
    assert 'Authorization token required' in data['error']


def test_invalid_token(client, test_user):
    """Test that invalid tokens are rejected."""
    headers = {'Authorization': 'Bearer invalid_token'}

    response = client.get('/api/training/projects/fake-id/videos', headers=headers)

    assert response.status_code == 401
    data = response.get_json()
    assert data['success'] is False
