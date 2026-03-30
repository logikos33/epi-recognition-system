"""
Test script for WebSocket and HLS streaming functionality
"""
import requests
import socketio
import time
import json

# Standard API test
BASE_URL = "http://localhost:5001"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_websocket_info():
    """Test WebSocket info endpoint"""
    print("\nTesting WebSocket info endpoint...")
    response = requests.get(f"{BASE_URL}/ws/test")
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    return response.status_code == 200

def test_websocket_connection():
    """Test WebSocket connection and events"""
    print("\nTesting WebSocket connection...")

    # Create SocketIO client
    sio = socketio.Client()

    # Event handlers
    @sio.on('connect')
    def on_connect():
        print('✅ Connected to WebSocket server')

    @sio.on('connected')
    def on_connected(data):
        print(f'✅ Received connected event: {data}')

    @sio.on('subscribed')
    def on_subscribed(data):
        print(f'✅ Subscribed to camera: {data}')

    @sio.on('detection')
    def on_detection(data):
        print(f'🎯 Detection received: {json.dumps(data, indent=2)}')

    @sio.on('disconnect')
    def on_disconnect():
        print('❌ Disconnected from WebSocket server')

    @sio.on('error')
    def on_error(data):
        print(f'❌ Error: {data}')

    try:
        # Connect to server
        sio.connect(f'{BASE_URL.replace("http", "ws")}/socket.io/', transports=['websocket'])

        # Subscribe to camera 1 (test)
        sio.emit('subscribe_camera', {'camera_id': 1})

        # Wait for events
        time.sleep(2)

        # Unsubscribe
        sio.emit('unsubscribe_camera', {'camera_id': 1})

        # Disconnect
        sio.disconnect()

        print('✅ WebSocket test completed')
        return True

    except Exception as e:
        print(f'❌ WebSocket test failed: {e}')
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("EPI Recognition System - WebSocket & HLS Test")
    print("=" * 60)

    # Run tests
    tests = [
        ("Health Check", test_health),
        ("WebSocket Info", test_websocket_info),
        ("WebSocket Connection", test_websocket_connection)
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f'❌ {name} failed with exception: {e}')
            results.append((name, False))

    # Print summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
