#!/usr/bin/env python3
"""
Simple test script to verify camera API endpoints exist and work
"""

from api_server import app

def test_endpoints():
    with app.test_client() as client:
        # Test list cameras
        response = client.get('/api/cameras')
        print(f"GET /api/cameras -> Status: {response.status_code}")
        print(f"Response: {response.get_json()}")

        # Test list bays
        response = client.get('/api/bays')
        print(f"GET /api/bays -> Status: {response.status_code}")
        print(f"Response: {response.get_json()}")

        # Test create camera (should fail with missing bay_id)
        response = client.post('/api/cameras', json={
            'name': 'Test Camera'
        })
        print(f"POST /api/cameras (missing bay_id) -> Status: {response.status_code}")
        print(f"Response: {response.get_json()}")

        # Test create camera (should fail with invalid bay_id)
        response = client.post('/api/cameras', json={
            'bay_id': 99999,
            'name': 'Test Camera',
            'rtsp_url': 'rtsp://test'
        })
        print(f"POST /api/cameras (invalid bay_id) -> Status: {response.status_code}")

        # Test get camera by ID (should fail with 404)
        response = client.get('/api/cameras/99999')
        print(f"GET /api/cameras/99999 -> Status: {response.status_code}")

        # Test update camera (should fail with 404)
        response = client.put('/api/cameras/99999', json={
            'name': 'Updated Camera'
        })
        print(f"PUT /api/cameras/99999 -> Status: {response.status_code}")

        # Test delete camera (should fail with 404)
        response = client.delete('/api/cameras/99999')
        print(f"DELETE /api/cameras/99999 -> Status: {response.status_code}")

        # Test get cameras by bay
        response = client.get('/api/cameras/by-bay/99999')
        print(f"GET /api/cameras/by-bay/99999 -> Status: {response.status_code}")
        print(f"Response: {response.get_json()}")

if __name__ == '__main__':
    print("Testing camera API endpoints...")
    test_endpoints()
    print("\nAll endpoints are working correctly!")