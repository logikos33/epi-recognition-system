# tests/test_camera_service.py
import pytest
from backend.database import get_db, engine
from backend.camera_service import CameraService
from sqlalchemy import text
import time


def test_create_camera():
    """Test creating a new camera"""
    db = next(get_db())
    # First get a bay_id
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    # Use unique camera name with timestamp
    timestamp = int(time.time())
    unique_name = f"Test Camera {timestamp}"

    camera = CameraService.create_camera(
        db=db,
        bay_id=bay_id,
        name=unique_name,
        rtsp_url="rtsp://test.local/stream",
        position_order=10
    )

    assert camera is not None
    assert camera['name'] == unique_name
    assert camera['rtsp_url'] == "rtsp://test.local/stream"
    assert camera['position_order'] == 10
    assert camera['is_active'] is True

    # Cleanup
    db.execute(text("DELETE FROM cameras WHERE id = :id"), {'id': camera['id']})
    db.commit()


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

    # Get the existing camera first
    result = db.execute(text("SELECT name FROM cameras WHERE id = :id"), {'id': camera_id})
    existing_name = result.scalar()

    # Use unique name for update
    timestamp = int(time.time())
    unique_name = f"Updated Camera {timestamp}"

    updated = CameraService.update_camera(
        db=db,
        camera_id=camera_id,
        name=unique_name,
        rtsp_url="rtsp://updated.local/stream"
    )

    assert updated['name'] == unique_name
    assert updated['rtsp_url'] == "rtsp://updated.local/stream"

    # Cleanup
    db.execute(text("DELETE FROM cameras WHERE id = :id"), {'id': camera_id})
    db.commit()


def test_delete_camera():
    """Test deleting a camera"""
    db = next(get_db())

    # Create a camera to delete
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    timestamp = int(time.time())
    unique_name = f"To Delete {timestamp}"

    camera = CameraService.create_camera(
        db=db,
        bay_id=bay_id,
        name=unique_name,
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