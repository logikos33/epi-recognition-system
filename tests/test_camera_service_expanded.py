"""
Tests for expanded CameraService with IP camera CRUD operations
"""
import pytest
import uuid
from unittest.mock import Mock
from backend.camera_service import CameraService
from backend.rtsp_builder import RTSPBuilder


class TestCameraServiceExpanded:
    """Test cases for CameraService IP camera CRUD operations"""

    def test_create_ip_camera(self):
        """Test creating a new IP camera with user_id"""
        # Mock database
        db = Mock()
        db.commit = Mock()

        # Mock execute result
        user_id = str(uuid.uuid4())
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda i: {
            0: 1,  # id
            1: user_id,  # user_id
            2: "Test Camera",  # name
            3: "intelbras",  # manufacturer
            4: "ip",  # type
            5: "192.168.1.100",  # ip
            6: 554,  # port
            7: "admin",  # username
            8: "password",  # password
            9: 1,  # channel
            10: 1,  # subtype
            11: "rtsp://test/stream",  # rtsp_url
            12: True,  # is_active
            13: None,  # last_connected_at
            14: None,  # connection_error
            15: None,  # created_at
        }[i])
        result = Mock()
        result.fetchone.return_value = mock_row
        db.execute.return_value = result

        # Test data
        camera_data = {
            'user_id': user_id,
            'name': 'Test Camera',
            'manufacturer': 'intelbras',
            'ip': '192.168.1.100',
            'port': 554,
            'username': 'admin',
            'password': 'password',
            'channel': 1,
            'subtype': 1,
            'is_active': True
        }

        # Execute
        camera = CameraService.create_camera(db, **camera_data)

        # Verify
        assert camera is not None
        assert camera['name'] == 'Test Camera'
        assert camera['user_id'] == user_id
        assert camera['is_active'] is True

        # Verify SQL call
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    def test_create_camera_generates_rtsp_url(self):
        """Test that RTSP URL is auto-generated when not provided"""
        # Mock database
        db = Mock()
        db.commit = Mock()

        # Mock execute result
        user_id = str(uuid.uuid4())
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda i: {
            0: 1,  # id
            1: user_id,  # user_id
            2: "Test Camera",  # name
            3: "intelbras",  # manufacturer
            4: "ip",  # type
            5: "192.168.1.100",  # ip
            6: 554,  # port
            7: None,  # username
            8: None,  # password
            9: 1,  # channel
            10: 1,  # subtype
            11: "rtsp://192.168.1.100:554/cam/realmonitor?channel=1&subtype=1",  # rtsp_url
            12: True,  # is_active
            13: None,  # last_connected_at
            14: None,  # connection_error
            15: None,  # created_at
        }[i])
        result = Mock()
        result.fetchone.return_value = mock_row
        db.execute.return_value = result

        # Test data without rtsp_url
        camera_data = {
            'user_id': user_id,
            'name': 'Test Camera',
            'manufacturer': 'intelbras',
            'ip': '192.168.1.100',
            'port': 554,
            'channel': 1,
            'subtype': 1,
            'is_active': True
            # Note: rtsp_url not provided
        }

        # Execute
        camera = CameraService.create_camera(db, **camera_data)

        # Verify RTSP URL was generated
        assert camera is not None
        assert 'rtsp_url' in camera
        assert camera['rtsp_url'] is not None

        # Verify RTSPBuilder was used
        expected_url = RTSPBuilder.build_url({
            'manufacturer': 'intelbras',
            'ip': '192.168.1.100',
            'port': 554,
            'username': '',
            'password': '',
            'channel': 1,
            'subtype': 1
        })
        assert camera['rtsp_url'] == expected_url

    def test_list_user_cameras(self):
        """Test listing all cameras for a specific user"""
        # Mock database
        db = Mock()

        # Mock execute result
        user_id = str(uuid.uuid4())
        mock_rows = [
            Mock(),
            Mock()
        ]
        mock_rows[0].__getitem__ = Mock(side_effect=lambda i: {
            0: 1,  # id
            1: user_id,  # user_id
            2: "Camera 1",  # name
            3: "intelbras",  # manufacturer
            4: "ip",  # type
            5: "192.168.1.100",  # ip
            6: 554,  # port
            7: None,  # username
            8: None,  # password
            9: 1,  # channel
            10: 1,  # subtype
            11: "rtsp://test/stream1",  # rtsp_url
            12: True,  # is_active
            13: None,  # last_connected_at
            14: None,  # connection_error
            15: None,  # created_at
        }[i])
        mock_rows[1].__getitem__ = Mock(side_effect=lambda i: {
            0: 2,  # id
            1: user_id,  # user_id
            2: "Camera 2",  # name
            3: "hikvision",  # manufacturer
            4: "ip",  # type
            5: "192.168.1.101",  # ip
            6: 554,  # port
            7: None,  # username
            8: None,  # password
            9: 1,  # channel
            10: 1,  # subtype
            11: "rtsp://test/stream2",  # rtsp_url
            12: False,  # is_active
            13: None,  # last_connected_at
            14: None,  # connection_error
            15: None,  # created_at
        }[i])
        result = Mock()
        result.fetchall.return_value = mock_rows
        db.execute.return_value = result

        # Execute
        cameras = CameraService.list_cameras_by_user(db, user_id)

        # Verify
        assert len(cameras) == 2
        assert all('id' in camera for camera in cameras)
        assert all('name' in camera for camera in cameras)
        assert all('rtsp_url' in camera for camera in cameras)
        assert all('manufacturer' in camera for camera in cameras)

        # Verify SQL call
        db.execute.assert_called_once()

    def test_get_camera_by_id(self):
        """Test getting a single camera by ID"""
        # Mock database
        db = Mock()

        # Mock execute result
        user_id = str(uuid.uuid4())
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda i: {
            0: 1,  # id
            1: user_id,  # user_id
            2: "Test Camera",  # name
            3: "intelbras",  # manufacturer
            4: "ip",  # type
            5: "192.168.1.100",  # ip
            6: 554,  # port
            7: None,  # username
            8: None,  # password
            9: 1,  # channel
            10: 1,  # subtype
            11: "rtsp://test/stream",  # rtsp_url
            12: True,  # is_active
            13: None,  # last_connected_at
            14: None,  # connection_error
            15: None,  # created_at
        }[i])
        result = Mock()
        result.fetchone.return_value = mock_row
        db.execute.return_value = result

        # Execute
        camera_id = 1
        camera = CameraService.get_camera_by_id(db, camera_id)

        # Verify
        assert camera is not None
        assert camera['id'] == camera_id
        assert camera['name'] == 'Test Camera'
        assert camera['rtsp_url'] == 'rtsp://test/stream'

        # Verify SQL call
        db.execute.assert_called_once()

    def test_update_camera(self):
        """Test updating camera fields"""
        # Mock database
        db = Mock()
        db.commit = Mock()

        # Mock execute result
        user_id = str(uuid.uuid4())
        mock_row = Mock()
        mock_row.__getitem__ = Mock(side_effect=lambda i: {
            0: 1,  # id
            1: user_id,  # user_id
            2: "Updated Camera",  # name
            3: "intelbras",  # manufacturer
            4: "ip",  # type
            5: "192.168.1.100",  # ip
            6: 554,  # port
            7: None,  # username
            8: None,  # password
            9: 1,  # channel
            10: 1,  # subtype
            11: "rtsp://updated/stream",  # rtsp_url
            12: False,  # is_active
            13: None,  # last_connected_at
            14: None,  # connection_error
            15: None,  # created_at
        }[i])
        result = Mock()
        result.fetchone.return_value = mock_row
        db.execute.return_value = result

        # Execute
        camera_id = 1
        updates = {
            'name': 'Updated Camera',
            'is_active': False,
            'rtsp_url': 'rtsp://updated/stream'
        }
        camera = CameraService.update_camera(db, camera_id, **updates)

        # Verify
        assert camera is not None
        assert camera['name'] == 'Updated Camera'
        assert camera['is_active'] is False
        assert camera['rtsp_url'] == 'rtsp://updated/stream'

        # Verify SQL call
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    def test_delete_camera(self):
        """Test deleting a camera"""
        # Mock database
        db = Mock()
        db.commit = Mock()

        # Mock execute result
        result = Mock()
        result.rowcount = 1  # Successfully deleted
        db.execute.return_value = result

        # Execute
        camera_id = 1
        deleted = CameraService.delete_camera(db, camera_id)

        # Verify
        assert deleted is True

        # Verify SQL call
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    def test_delete_camera_not_found(self):
        """Test deleting a non-existent camera"""
        # Mock database
        db = Mock()
        db.commit = Mock()

        # Mock execute result
        result = Mock()
        result.rowcount = 0  # Not found
        db.execute.return_value = result

        # Execute
        camera_id = 999
        deleted = CameraService.delete_camera(db, camera_id)

        # Verify
        assert deleted is False

        # Verify SQL call (should still try to delete)
        db.execute.assert_called_once()
        db.commit.assert_called_once()