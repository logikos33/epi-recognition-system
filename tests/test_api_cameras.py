# tests/test_api_cameras.py
import pytest
import json
from api_server import app


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Create a test token
        response = client.post('/api/auth/login', json={
            'email': 'test@local.dev',
            'password': '123456'
        })
        data = json.loads(response.data)
        token = data.get('token')

        # Set Authorization header for all requests
        client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        yield client


def test_list_cameras(client):
    """Test GET /api/cameras"""
    response = client.get('/api/cameras')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['success'] is True
    assert 'cameras' in data
    assert isinstance(data['cameras'], list)


def test_create_camera(client):
    """Test POST /api/cameras"""
    # Get a bay_id first
    response = client.get('/api/bays')
    bays_data = json.loads(response.data)
    bay_id = bays_data['bays'][0]['id']

    response = client.post('/api/cameras', json={
        'bay_id': bay_id,
        'name': 'API Test Camera',
        'rtsp_url': 'rtsp://test.api/stream'
    })
    data = json.loads(response.data)

    assert response.status_code == 201
    assert data['success'] is True
    assert data['camera']['name'] == 'API Test Camera'


def test_get_camera_by_id(client):
    """Test GET /api/cameras/<id>"""
    # List cameras to get an ID
    response = client.get('/api/cameras')
    data = json.loads(response.data)
    camera_id = data['cameras'][0]['id']

    response = client.get(f'/api/cameras/{camera_id}')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['success'] is True
    assert data['camera']['id'] == camera_id


def test_update_camera(client):
    """Test PUT /api/cameras/<id>"""
    # List cameras to get an ID
    response = client.get('/api/cameras')
    data = json.loads(response.data)
    camera_id = data['cameras'][0]['id']

    response = client.put(f'/api/cameras/{camera_id}', json={
        'name': 'Updated via API'
    })
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['success'] is True
    assert data['camera']['name'] == 'Updated via API'


def test_delete_camera(client):
    """Test DELETE /api/cameras/<id>"""
    # Create a camera to delete
    response = client.get('/api/bays')
    bays_data = json.loads(response.data)
    bay_id = bays_data['bays'][0]['id']

    create_response = client.post('/api/cameras', json={
        'bay_id': bay_id,
        'name': 'To Delete via API'
    })
    create_data = json.loads(create_response.data)
    camera_id = create_data['camera']['id']

    # Delete it
    response = client.delete(f'/api/cameras/{camera_id}')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['success'] is True