# tests/test_annotation_db.py
import pytest
import uuid
from sqlalchemy import text
from backend.database import get_db
from backend.annotation_db import AnnotationDB


@pytest.fixture
def db():
    """Get database connection for tests."""
    db_session = next(get_db())
    yield db_session
    db_session.rollback()
    db_session.close()


@pytest.fixture
def test_user(db):
    """Create a test user for foreign key constraints."""
    user_id = str(uuid.uuid4())

    # Create user with hashed password
    import bcrypt
    password_hash = bcrypt.hashpw("test_password".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    query = text("""
        INSERT INTO users (id, email, password_hash, full_name, is_active)
        VALUES (:user_id, :email, :password_hash, :full_name, TRUE)
        ON CONFLICT (email) DO NOTHING
    """)

    db.execute(query, {
        'user_id': user_id,
        'email': f'test-{user_id}@example.com',
        'password_hash': password_hash,
        'full_name': 'Test User'
    })
    db.commit()

    yield user_id

    # Cleanup
    db.execute(text("DELETE FROM training_projects WHERE user_id = :user_id"), {'user_id': user_id})
    db.execute(text("DELETE FROM users WHERE id = :user_id"), {'user_id': user_id})
    db.commit()


@pytest.fixture
def test_project(db, test_user):
    """Create a test project with video and frame."""
    from backend.training_db import TrainingProjectDB
    from backend.video_db import VideoService
    import uuid

    project_db = TrainingProjectDB()
    video_service = VideoService()

    project = project_db.create_project(
        db=db,
        user_id=test_user,
        name="Test Project",
        description="Test",
        target_classes=["helmet", "vest"]
    )

    video = video_service.upload_video(
        db=db,
        project_id=project['id'],
        user_id=test_user,
        filename="test.mp4",
        storage_path="/tmp/test.mp4",
        duration=10.0,
        frame_count=300,
        fps=30.0
    )

    # Create frame directly
    frame_id = str(uuid.uuid4())
    query = text("""
        INSERT INTO training_frames (id, video_id, frame_number, storage_path)
        VALUES (:frame_id, :video_id, :frame_number, :storage_path)
        RETURNING id, video_id, frame_number, storage_path, is_annotated, created_at
    """)
    result = db.execute(query, {
        'frame_id': frame_id,
        'video_id': video['id'],
        'frame_number': 0,
        'storage_path': "/tmp/frame_000000.jpg"
    })
    db.commit()
    row = result.fetchone()

    frame = {
        'id': str(row[0]),
        'video_id': str(row[1]),
        'frame_number': row[2],
        'storage_path': row[3],
        'is_annotated': row[4],
        'created_at': row[5].isoformat()
    }

    yield {'project': project, 'video': video, 'frame': frame}


def test_create_annotation(db, test_user, test_project):
    """Test creating a new annotation"""
    annotation_db = AnnotationDB()
    frame = test_project['frame']

    annotation = annotation_db.create_annotation(
        db=db,
        frame_id=frame['id'],
        class_name="helmet",
        bbox_x=100.5,
        bbox_y=200.3,
        bbox_width=50.0,
        bbox_height=60.0,
        is_ai_generated=False,
        created_by=test_user
    )

    assert annotation is not None
    assert annotation['class_name'] == "helmet"
    assert annotation['bbox_x'] == 100.5
    assert annotation['bbox_y'] == 200.3
    assert annotation['bbox_width'] == 50.0
    assert annotation['bbox_height'] == 60.0
    assert annotation['is_ai_generated'] is False
    assert annotation['created_by'] == test_user


def test_get_frame_annotations(db, test_user, test_project):
    """Test getting all annotations for a frame"""
    annotation_db = AnnotationDB()
    frame = test_project['frame']

    # Create multiple annotations
    annotation_db.create_annotation(
        db=db,
        frame_id=frame['id'],
        class_name="helmet",
        bbox_x=100.0,
        bbox_y=200.0,
        bbox_width=50.0,
        bbox_height=60.0
    )

    annotation_db.create_annotation(
        db=db,
        frame_id=frame['id'],
        class_name="vest",
        bbox_x=300.0,
        bbox_y=400.0,
        bbox_width=80.0,
        bbox_height=100.0
    )

    # Get all annotations
    annotations = annotation_db.get_frame_annotations(db, frame['id'])

    assert len(annotations) == 2
    assert annotations[0]['class_name'] in ["helmet", "vest"]
    assert annotations[1]['class_name'] in ["helmet", "vest"]


def test_update_annotation(db, test_user, test_project):
    """Test updating an existing annotation"""
    annotation_db = AnnotationDB()
    frame = test_project['frame']

    # Create annotation
    annotation = annotation_db.create_annotation(
        db=db,
        frame_id=frame['id'],
        class_name="helmet",
        bbox_x=100.0,
        bbox_y=200.0,
        bbox_width=50.0,
        bbox_height=60.0
    )

    # Update annotation
    updated = annotation_db.update_annotation(
        db=db,
        annotation_id=annotation['id'],
        class_name="helmet",
        bbox_x=150.0,
        bbox_y=250.0,
        bbox_width=55.0,
        bbox_height=65.0
    )

    assert updated is True

    # Verify update
    annotations = annotation_db.get_frame_annotations(db, frame['id'])
    assert len(annotations) == 1
    assert annotations[0]['bbox_x'] == 150.0
    assert annotations[0]['bbox_y'] == 250.0
    assert annotations[0]['bbox_width'] == 55.0
    assert annotations[0]['bbox_height'] == 65.0


def test_delete_annotation(db, test_user, test_project):
    """Test deleting an annotation"""
    annotation_db = AnnotationDB()
    frame = test_project['frame']

    # Create annotation
    annotation = annotation_db.create_annotation(
        db=db,
        frame_id=frame['id'],
        class_name="helmet",
        bbox_x=100.0,
        bbox_y=200.0,
        bbox_width=50.0,
        bbox_height=60.0
    )

    # Delete annotation
    deleted = annotation_db.delete_annotation(db, annotation['id'])
    assert deleted is True

    # Verify deletion
    annotations = annotation_db.get_frame_annotations(db, frame['id'])
    assert len(annotations) == 0
