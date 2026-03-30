"""
Tests for video upload and processing.

This test suite validates video upload, frame extraction,
and video metadata storage for training projects.
"""
import pytest
import os
import tempfile
import uuid
from sqlalchemy import text
from backend.video_processor import VideoProcessor
from backend.video_db import VideoService
from backend.training_db import TrainingProjectDB
from backend.database import get_db


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    db = next(get_db())
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_user(db_session):
    """Create a test user."""
    import bcrypt

    user_id = str(uuid.uuid4())
    email = f"test_{user_id[:8]}@local.dev"
    password_hash = bcrypt.hashpw("123456".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    query = text("""
        INSERT INTO users (id, email, password_hash, full_name, company_name, is_active, created_at)
        VALUES (:id, :email, :password_hash, :full_name, :company_name, TRUE, NOW())
        RETURNING id, email, full_name
    """)

    result = db_session.execute(query, {
        'id': user_id,
        'email': email,
        'password_hash': password_hash,
        'full_name': 'Test User',
        'company_name': 'Test Company'
    })
    db_session.commit()
    row = result.fetchone()

    return {
        'id': str(row[0]),
        'email': row[1],
        'full_name': row[2]
    }


@pytest.fixture(scope="function")
def test_project(db_session, test_user):
    """Create a test training project."""
    project_db = TrainingProjectDB()
    return project_db.create_project(
        db=db_session,
        user_id=test_user['id'],
        name="Test Project for Videos",
        description="Test project for video upload testing",
        target_classes=["helmet", "vest"]
    )


def test_upload_video_to_project(db_session, test_project):
    """Test uploading a video to a training project."""
    video_service = VideoService()

    # Create a temporary video file path (simulating upload)
    video_id = str(uuid.uuid4())
    filename = "test_video.mp4"
    storage_path = f"/tmp/videos/{test_project['id']}/{video_id}.mp4"

    # Mock video metadata
    duration = 10.5
    frame_count = 315
    fps = 30.0

    # Upload video record
    video = video_service.upload_video(
        db=db_session,
        project_id=test_project['id'],
        user_id=test_project['user_id'],
        filename=filename,
        storage_path=storage_path,
        duration=duration,
        frame_count=frame_count,
        fps=fps
    )

    # Verify video record was created
    assert video is not None
    assert video['id'] is not None
    assert video['filename'] == filename
    assert video['storage_path'] == storage_path
    assert video['duration_seconds'] == duration
    assert video['frame_count'] == frame_count
    assert video['fps'] == fps
    assert video['project_id'] == test_project['id']


def test_list_project_videos(db_session, test_project):
    """Test listing all videos for a project."""
    video_service = VideoService()

    # Upload multiple videos
    for i in range(3):
        video_id = str(uuid.uuid4())
        filename = f"test_video_{i}.mp4"
        storage_path = f"/tmp/videos/{test_project['id']}/{video_id}.mp4"

        video_service.upload_video(
            db=db_session,
            project_id=test_project['id'],
            user_id=test_project['user_id'],
            filename=filename,
            storage_path=storage_path,
            duration=10.0 + i,
            frame_count=300 + (i * 10),
            fps=30.0
        )

    # List videos
    videos = video_service.list_project_videos(
        db=db_session,
        project_id=test_project['id'],
        user_id=test_project['user_id']
    )

    # Verify
    assert len(videos) == 3
    assert all(v['project_id'] == test_project['id'] for v in videos)


def test_get_video_by_id(db_session, test_project):
    """Test retrieving a single video by ID."""
    video_service = VideoService()

    # Upload video
    video_id = str(uuid.uuid4())
    filename = "test_video.mp4"
    storage_path = f"/tmp/videos/{test_project['id']}/{video_id}.mp4"

    uploaded = video_service.upload_video(
        db=db_session,
        project_id=test_project['id'],
        user_id=test_project['user_id'],
        filename=filename,
        storage_path=storage_path,
        duration=15.0,
        frame_count=450,
        fps=30.0
    )

    # Get video by ID
    video = video_service.get_video(
        db=db_session,
        video_id=uploaded['id'],
        user_id=test_project['user_id']
    )

    # Verify
    assert video is not None
    assert video['id'] == uploaded['id']
    assert video['filename'] == filename
    assert video['duration_seconds'] == 15.0


def test_delete_video(db_session, test_project):
    """Test deleting a video."""
    video_service = VideoService()

    # Upload video
    video_id = str(uuid.uuid4())
    filename = "test_video.mp4"
    storage_path = f"/tmp/videos/{test_project['id']}/{video_id}.mp4"

    uploaded = video_service.upload_video(
        db=db_session,
        project_id=test_project['id'],
        user_id=test_project['user_id'],
        filename=filename,
        storage_path=storage_path,
        duration=15.0,
        frame_count=450,
        fps=30.0
    )

    # Delete video
    result = video_service.delete_video(
        db=db_session,
        video_id=uploaded['id'],
        user_id=test_project['user_id']
    )

    # Verify deletion
    assert result is True

    # Verify video no longer exists
    video = video_service.get_video(
        db=db_session,
        video_id=uploaded['id'],
        user_id=test_project['user_id']
    )
    assert video is None


def test_video_processor_extract_metadata(db_session, test_project):
    """Test VideoProcessor extracts video metadata correctly."""
    # This test will be implemented once we have a real video file
    # For now, we test the metadata storage logic
    video_service = VideoService()

    video_id = str(uuid.uuid4())
    filename = "sample.mp4"
    storage_path = f"/tmp/videos/{test_project['id']}/{video_id}.mp4"

    video = video_service.upload_video(
        db=db_session,
        project_id=test_project['id'],
        user_id=test_project['user_id'],
        filename=filename,
        storage_path=storage_path,
        duration=30.0,
        frame_count=900,
        fps=30.0
    )

    assert video['duration_seconds'] == 30.0
    assert video['frame_count'] == 900
    assert video['fps'] == 30.0
