# tests/test_camera_service.py
import pytest
from backend.database import get_db, engine
from backend.camera_service import CameraService
from sqlalchemy import text


def test_create_camera():
    """Test creating a new camera"""
    db = next(get_db())
    # First get a bay_id
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    camera = CameraService.create_camera(
        db=db,
        bay_id=bay_id,
        name="Test Camera",
        rtsp_url="rtsp://test.local/stream",
        position_order=10
    )

    assert camera is not None
    assert camera['name'] == "Test Camera"
    assert camera['rtsp_url'] == "rtsp://test.local/stream"
    assert camera['position_order'] == 10
    assert camera['is_active'] is True


def test_list_cameras():
    """Test listing all cameras"""
    db = next(get_db())
    cameras = CameraService.list_cameras(db)

    assert isinstance(cameras, list)
    assert len(cameras) >= 5  # We inserted 5 in migration


def test_get_camera_by_id():
    """Test getting a specific camera"""
    db = next(get_db())
    # Get first camera ID
    result = db.execute(text("SELECT id FROM cameras LIMIT 1"))
    camera_id = result.scalar()

    camera = CameraService.get_camera_by_id(db, camera_id)

    assert camera is not None
    assert camera['id'] == camera_id
    assert 'name' in camera


def test_update_camera():
    """Test updating camera details"""
    db = next(get_db())
    # Get first camera ID
    result = db.execute(text("SELECT id FROM cameras LIMIT 1"))
    camera_id = result.scalar()

    updated = CameraService.update_camera(
        db=db,
        camera_id=camera_id,
        name="Updated Camera Name",
        rtsp_url="rtsp://updated.local/stream"
    )

    assert updated['name'] == "Updated Camera Name"
    assert updated['rtsp_url'] == "rtsp://updated.local/stream"


def test_delete_camera():
    """Test deleting a camera"""
    db = next(get_db())

    # Create a camera to delete
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    camera = CameraService.create_camera(
        db=db,
        bay_id=bay_id,
        name="To Delete",
        rtsp_url="rtsp://delete.local/stream"
    )
    camera_id = camera['id']

    # Delete it
    success = CameraService.delete_camera(db, camera_id)
    assert success is True

    # Verify it's gone
    result = db.execute(
        text("SELECT * FROM cameras WHERE id = :id"),
        {'id': camera_id}
    )
    deleted = result.fetchone()
    assert deleted is None


def test_get_cameras_by_bay():
    """Test getting cameras for a specific bay"""
    db = next(get_db())
    # Get first bay_id
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    cameras = CameraService.get_cameras_by_bay(db, bay_id)

    assert isinstance(cameras, list)
    for camera in cameras:
        assert camera['bay_id'] == bay_id