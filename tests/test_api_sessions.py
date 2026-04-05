# tests/test_api_sessions.py
import pytest
import json
from datetime import datetime
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


def test_create_session(client):
    """Test POST /api/sessions"""
    # Get a bay_id and camera_id first
    response = client.get('/api/bays')
    bays_data = json.loads(response.data)
    bay_id = bays_data['bays'][0]['id']

    response = client.get('/api/cameras')
    cameras_data = json.loads(response.data)
    camera_id = cameras_data['cameras'][0]['id']

    # Use timestamp to avoid duplicate license plate conflicts
    timestamp = datetime.now().strftime('%H%M%S')  # Only time part to stay under 20 chars
    license_plate = f'T{timestamp}'  # Format: THHMMSS (7 chars)

    response = client.post('/api/sessions', json={
        'bay_id': bay_id,
        'camera_id': camera_id,
        'license_plate': license_plate
    })
    data = json.loads(response.data)

    assert response.status_code == 201
    assert data['success'] is True
    assert data['session']['license_plate'] == license_plate
    assert data['session']['bay_id'] == bay_id
    assert data['session']['camera_id'] == camera_id
    assert data['session']['status'] == 'active'


def test_list_sessions(client):
    """Test GET /api/sessions"""
    response = client.get('/api/sessions')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['success'] is True
    assert 'sessions' in data
    assert isinstance(data['sessions'], list)


def test_list_sessions_with_filters(client):
    """Test GET /api/sessions with query parameters"""
    # Create a session first
    response = client.get('/api/bays')
    bays_data = json.loads(response.data)
    bay_id = bays_data['bays'][0]['id']

    response = client.get('/api/cameras')
    cameras_data = json.loads(response.data)
    camera_id = cameras_data['cameras'][0]['id']

    timestamp = datetime.now().strftime('%H%M%S')
    license_plate = f'F{timestamp}'

    create_response = client.post('/api/sessions', json={
        'bay_id': bay_id,
        'camera_id': camera_id,
        'license_plate': license_plate
    })

    # Filter by bay_id
    response = client.get(f'/api/sessions?bay_id={bay_id}')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['success'] is True
    assert 'sessions' in data

    # Filter by status
    response = client.get('/api/sessions?status=active')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['success'] is True

    # Filter with limit
    response = client.get('/api/sessions?limit=5')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['success'] is True


def test_get_session_by_id(client):
    """Test GET /api/sessions/<id>"""
    # Create a session first
    response = client.get('/api/bays')
    bays_data = json.loads(response.data)
    bay_id = bays_data['bays'][0]['id']

    response = client.get('/api/cameras')
    cameras_data = json.loads(response.data)
    camera_id = cameras_data['cameras'][0]['id']

    timestamp = datetime.now().strftime('%H%M%S')
    license_plate = f'G{timestamp}'

    create_response = client.post('/api/sessions', json={
        'bay_id': bay_id,
        'camera_id': camera_id,
        'license_plate': license_plate
    })
    create_data = json.loads(create_response.data)
    session_id = create_data['session']['id']

    # Get the session
    response = client.get(f'/api/sessions/{session_id}')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['success'] is True
    assert data['session']['id'] == session_id
    assert data['session']['license_plate'] == license_plate


def test_get_session_not_found(client):
    """Test GET /api/sessions/<id> with invalid ID"""
    response = client.get('/api/sessions/00000000-0000-0000-0000-000000000000')
    data = json.loads(response.data)

    assert response.status_code == 404
    assert data['success'] is False
    assert 'not found' in data['error'].lower()


def test_update_session(client):
    """Test PUT /api/sessions/<id>"""
    # Create a session first
    response = client.get('/api/bays')
    bays_data = json.loads(response.data)
    bay_id = bays_data['bays'][0]['id']

    response = client.get('/api/cameras')
    cameras_data = json.loads(response.data)
    camera_id = cameras_data['cameras'][0]['id']

    timestamp = datetime.now().strftime('%H%M%S')
    license_plate = f'U{timestamp}'

    create_response = client.post('/api/sessions', json={
        'bay_id': bay_id,
        'camera_id': camera_id,
        'license_plate': license_plate
    })
    create_data = json.loads(create_response.data)
    session_id = create_data['session']['id']

    # Update the session
    response = client.put(f'/api/sessions/{session_id}', json={
        'license_plate': f'U{timestamp}-X',
        'final_weight': 1500.5
    })
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['success'] is True
    assert data['session']['license_plate'] == f'U{timestamp}-X'
    assert data['session']['final_weight'] == 1500.5


def test_complete_session(client):
    """Test POST /api/sessions/<id>/complete"""
    # Create a session first
    response = client.get('/api/bays')
    bays_data = json.loads(response.data)
    bay_id = bays_data['bays'][0]['id']

    response = client.get('/api/cameras')
    cameras_data = json.loads(response.data)
    camera_id = cameras_data['cameras'][0]['id']

    timestamp = datetime.now().strftime('%H%M%S')
    license_plate = f'C{timestamp}'

    create_response = client.post('/api/sessions', json={
        'bay_id': bay_id,
        'camera_id': camera_id,
        'license_plate': license_plate
    })
    create_data = json.loads(create_response.data)
    session_id = create_data['session']['id']

    # Complete the session
    response = client.post(f'/api/sessions/{session_id}/complete')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['success'] is True
    assert data['session']['status'] == 'completed'
    assert data['session']['truck_exit_time'] is not None
    assert data['session']['duration_seconds'] is not None


def test_add_counted_product(client):
    """Test POST /api/sessions/<id>/products"""
    # Create a session first
    response = client.get('/api/bays')
    bays_data = json.loads(response.data)
    bay_id = bays_data['bays'][0]['id']

    response = client.get('/api/cameras')
    cameras_data = json.loads(response.data)
    camera_id = cameras_data['cameras'][0]['id']

    timestamp = datetime.now().strftime('%H%M%S')
    license_plate = f'P{timestamp}'

    create_response = client.post('/api/sessions', json={
        'bay_id': bay_id,
        'camera_id': camera_id,
        'license_plate': license_plate
    })
    create_data = json.loads(create_response.data)
    session_id = create_data['session']['id']

    # Add a counted product
    response = client.post(f'/api/sessions/{session_id}/products', json={
        'product_type': 'diesel',
        'quantity': 100,
        'confidence': 0.95,
        'confirmed_by_user': True
    })
    data = json.loads(response.data)

    assert response.status_code == 201
    assert data['success'] is True
    assert data['product']['product_type'] == 'diesel'
    assert data['product']['quantity'] == 100
    assert data['product']['confidence'] == 0.95
    assert data['product']['confirmed_by_user'] is True


def test_get_session_products(client):
    """Test GET /api/sessions/<id>/products"""
    # Create a session first
    response = client.get('/api/bays')
    bays_data = json.loads(response.data)
    bay_id = bays_data['bays'][0]['id']

    response = client.get('/api/cameras')
    cameras_data = json.loads(response.data)
    camera_id = cameras_data['cameras'][0]['id']

    timestamp = datetime.now().strftime('%H%M%S')
    license_plate = f'L{timestamp}'

    create_response = client.post('/api/sessions', json={
        'bay_id': bay_id,
        'camera_id': camera_id,
        'license_plate': license_plate
    })
    create_data = json.loads(create_response.data)
    session_id = create_data['session']['id']

    # Add some products
    client.post(f'/api/sessions/{session_id}/products', json={
        'product_type': 'diesel',
        'quantity': 100,
        'confidence': 0.95
    })

    client.post(f'/api/sessions/{session_id}/products', json={
        'product_type': 'adblue',
        'quantity': 50,
        'confidence': 0.88
    })

    # Get the products
    response = client.get(f'/api/sessions/{session_id}/products')
    data = json.loads(response.data)

    assert response.status_code == 200
    assert data['success'] is True
    assert 'products' in data
    assert isinstance(data['products'], list)
    assert len(data['products']) >= 2


def test_unauthorized_access():
    """Test that unauthorized requests are rejected"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Test POST without token
        response = client.post('/api/sessions', json={
            'bay_id': 1,
            'camera_id': 1,
            'license_plate': 'TEST-123'
        })
        assert response.status_code == 401

        # Test GET without token
        response = client.get('/api/sessions')
        assert response.status_code == 401

        # Test GET by ID without token
        response = client.get('/api/sessions/some-id')
        assert response.status_code == 401

        # Test PUT without token
        response = client.put('/api/sessions/some-id', json={'license_plate': 'NEW'})
        assert response.status_code == 401

        # Test complete without token
        response = client.post('/api/sessions/some-id/complete')
        assert response.status_code == 401

        # Test add product without token
        response = client.post('/api/sessions/some-id/products', json={
            'product_type': 'diesel',
            'quantity': 100
        })
        assert response.status_code == 401

        # Test get products without token
        response = client.get('/api/sessions/some-id/products')
        assert response.status_code == 401


def test_invalid_session_id_for_operations(client):
    """Test operations with invalid session ID"""
    invalid_id = '00000000-0000-0000-0000-000000000000'

    # Try to update
    response = client.put(f'/api/sessions/{invalid_id}', json={
        'license_plate': 'NEW'
    })
    assert response.status_code == 404

    # Try to complete
    response = client.post(f'/api/sessions/{invalid_id}/complete')
    assert response.status_code == 404

    # Try to add product
    response = client.post(f'/api/sessions/{invalid_id}/products', json={
        'product_type': 'diesel',
        'quantity': 100
    })
    assert response.status_code == 404

    # Try to get products
    response = client.get(f'/api/sessions/{invalid_id}/products')
    data = json.loads(response.data)
    # Should succeed but return empty list
    assert response.status_code == 200
    assert data['products'] == []
