# tests/test_api_ocr.py
import pytest
import json
import os
import tempfile
from PIL import Image
import numpy as np
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


@pytest.fixture
def sample_license_plate_image():
    """Create a sample image for testing OCR"""
    # Create a simple test image with white background
    img = Image.new('RGB', (400, 100), color='white')

    # Add some random noise to simulate a photo
    pixels = np.array(img)
    noise = np.random.randint(0, 50, pixels.shape, dtype=np.uint8)
    pixels = np.clip(pixels + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(pixels)

    # Save to temp file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
    img.save(temp_file.name)
    temp_file.close()

    yield temp_file.name

    # Cleanup
    if os.path.exists(temp_file.name):
        os.remove(temp_file.name)


@pytest.fixture
def invalid_image_file():
    """Create a non-image file for testing validation"""
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.txt')
    temp_file.write(b'This is not an image')
    temp_file.close()

    yield temp_file.name

    # Cleanup
    if os.path.exists(temp_file.name):
        os.remove(temp_file.name)


def test_recognize_license_plate_success(client, sample_license_plate_image):
    """Test POST /api/ocr/recognize-license-plate with valid image"""
    with open(sample_license_plate_image, 'rb') as f:
        response = client.post(
            '/api/ocr/recognize-license-plate',
            data={'image': (f, 'test.png')},
            content_type='multipart/form-data'
        )

    data = json.loads(response.data)

    # Should succeed (even if OCR doesn't detect text, endpoint should work)
    assert response.status_code == 200
    assert data['success'] is True
    assert 'license_plate' in data
    assert 'confidence' in data
    assert 'valid' in data
    assert isinstance(data['confidence'], (int, float))


def test_recognize_license_plate_no_file(client):
    """Test POST /api/ocr/recognize-license-plate without image file"""
    response = client.post(
        '/api/ocr/recognize-license-plate',
        data={},
        content_type='multipart/form-data'
    )
    data = json.loads(response.data)

    assert response.status_code == 400
    assert data['success'] is False
    assert 'No image file provided' in data['error']


def test_recognize_license_plate_empty_filename(client):
    """Test POST /api/ocr/recognize-license-plate with empty filename"""
    response = client.post(
        '/api/ocr/recognize-license-plate',
        data={'image': (tempfile.SpooledTemporaryFile(), '')},
        content_type='multipart/form-data'
    )
    data = json.loads(response.data)

    assert response.status_code == 400
    assert data['success'] is False
    assert 'No image file selected' in data['error']


def test_recognize_license_plate_invalid_file_type(client, invalid_image_file):
    """Test POST /api/ocr/recognize-license-plate with invalid file type"""
    with open(invalid_image_file, 'rb') as f:
        response = client.post(
            '/api/ocr/recognize-license-plate',
            data={'image': (f, 'test.txt')},
            content_type='multipart/form-data'
        )

    data = json.loads(response.data)

    assert response.status_code == 400
    assert data['success'] is False
    assert 'Invalid file type' in data['error']


def test_recognize_license_plate_valid_file_types(client):
    """Test that all allowed file types are accepted"""
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.bmp']

    for ext in allowed_extensions:
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='white')
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        img.save(temp_file.name)
        temp_file.close()

        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    '/api/ocr/recognize-license-plate',
                    data={'image': (f, f'test{ext}')},
                    content_type='multipart/form-data'
                )

            # Should not return 400 for file type error
            assert response.status_code != 400 or 'Invalid file type' not in json.loads(response.data).get('error', '')

        finally:
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)


def test_unauthorized_access():
    """Test that unauthorized requests are rejected"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Create a simple test image
        img = Image.new('RGB', (100, 100), color='white')
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
        img.save(temp_file.name)
        temp_file.close()

        try:
            with open(temp_file.name, 'rb') as f:
                response = client.post(
                    '/api/ocr/recognize-license-plate',
                    data={'image': (f, 'test.png')},
                    content_type='multipart/form-data'
                )

            assert response.status_code == 401

        finally:
            if os.path.exists(temp_file.name):
                os.remove(temp_file.name)


def test_recognize_license_plate_jpeg_format(client):
    """Test with JPEG format specifically"""
    # Create a test image
    img = Image.new('RGB', (200, 100), color='white')
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    img.save(temp_file.name, 'JPEG')
    temp_file.close()

    try:
        with open(temp_file.name, 'rb') as f:
            response = client.post(
                '/api/ocr/recognize-license-plate',
                data={'image': (f, 'test.jpg')},
                content_type='multipart/form-data'
            )

        data = json.loads(response.data)
        assert response.status_code == 200
        assert data['success'] is True

    finally:
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)


def test_recognize_license_plate_bmp_format(client):
    """Test with BMP format specifically"""
    # Create a test image
    img = Image.new('RGB', (200, 100), color='white')
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.bmp')
    img.save(temp_file.name, 'BMP')
    temp_file.close()

    try:
        with open(temp_file.name, 'rb') as f:
            response = client.post(
                '/api/ocr/recognize-license-plate',
                data={'image': (f, 'test.bmp')},
                content_type='multipart/form-data'
            )

        data = json.loads(response.data)
        assert response.status_code == 200
        assert data['success'] is True

    finally:
        if os.path.exists(temp_file.name):
            os.remove(temp_file.name)


def test_recognize_license_plate_response_structure(client, sample_license_plate_image):
    """Test that response has all required fields"""
    with open(sample_license_plate_image, 'rb') as f:
        response = client.post(
            '/api/ocr/recognize-license-plate',
            data={'image': (f, 'test.png')},
            content_type='multipart/form-data'
        )

    data = json.loads(response.data)

    # Check all required fields exist
    assert 'success' in data
    assert 'license_plate' in data
    assert 'confidence' in data
    assert 'valid' in data

    # Check data types
    assert isinstance(data['success'], bool)
    assert isinstance(data['license_plate'], (str, type(None)))
    assert isinstance(data['confidence'], (int, float))
    assert isinstance(data['valid'], bool)

    # Check confidence range
    assert 0 <= data['confidence'] <= 100
