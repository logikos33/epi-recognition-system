# tests/test_yolo_exporter.py
import pytest
import uuid
import os
import tempfile
import shutil
from sqlalchemy import text
from backend.database import get_db
from backend.yolo_exporter import YOLOExporter


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
def test_project_with_annotations(db, test_user, tmp_path):
    """Create a test project with video, frames, and annotations."""
    from backend.training_db import TrainingProjectDB
    from backend.video_db import VideoService
    from backend.annotation_db import AnnotationDB

    project_db = TrainingProjectDB()
    video_service = VideoService()
    annotation_db = AnnotationDB()

    # Create project
    project = project_db.create_project(
        db=db,
        user_id=test_user,
        name="Test Project",
        description="Test",
        target_classes=["helmet", "vest", "gloves"]
    )

    # Create video
    video = video_service.upload_video(
        db=db,
        project_id=project['id'],
        user_id=test_user,
        filename="test.mp4",
        storage_path="/tmp/test.mp4",
        duration=10.0,
        frame_count=10,
        fps=30.0
    )

    # Create dummy frame images
    frame_ids = []
    for i in range(10):
        # Create dummy image file
        img_path = tmp_path / f"frame_{i:06d}.jpg"
        import cv2
        import numpy as np
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.imwrite(str(img_path), img)

        # Create frame in database
        frame_id = str(uuid.uuid4())
        query = text("""
            INSERT INTO training_frames (id, video_id, frame_number, storage_path, is_annotated)
            VALUES (:frame_id, :video_id, :frame_number, :storage_path, TRUE)
            RETURNING id
        """)
        result = db.execute(query, {
            'frame_id': frame_id,
            'video_id': video['id'],
            'frame_number': i,
            'storage_path': str(img_path)
        })
        db.commit()
        frame_ids.append(frame_id)

        # Add 2-3 annotations per frame
        num_annotations = (i % 2) + 2  # 2 or 3 annotations
        for j in range(num_annotations):
            class_name = ["helmet", "vest", "gloves"][j % 3]
            annotation_db.create_annotation(
                db=db,
                frame_id=frame_id,
                class_name=class_name,
                bbox_x=100.0 + j * 50,
                bbox_y=200.0 + j * 30,
                bbox_width=50.0 + j * 10,
                bbox_height=60.0 + j * 5,
                is_ai_generated=False
            )

    yield {
        'project': project,
        'video': video,
        'frame_ids': frame_ids,
        'target_classes': ["helmet", "vest", "gloves"]
    }


def test_export_dataset_to_yolo(db, test_project_with_annotations, tmp_path):
    """Test exporting annotations to YOLO format"""
    exporter = YOLOExporter()
    project_id = test_project_with_annotations['project']['id']

    result = exporter.export_project(
        db=db,
        project_id=project_id,
        output_dir=str(tmp_path),
        train_val_split=0.8
    )

    assert result['success'] is True
    assert os.path.exists(f'{tmp_path}/data.yaml')
    assert os.path.exists(f'{tmp_path}/images/train')
    assert os.path.exists(f'{tmp_path}/images/val')
    assert os.path.exists(f'{tmp_path}/labels/train')
    assert os.path.exists(f'{tmp_path}/labels/val')

    # Check data.yaml content
    with open(f'{tmp_path}/data.yaml', 'r') as f:
        yaml_content = f.read()
    assert 'path:' in yaml_content
    assert 'train: images/train' in yaml_content
    assert 'val: images/val' in yaml_content
    assert 'nc: 3' in yaml_content  # 3 classes
    assert 'names: [' in yaml_content
    assert 'helmet' in yaml_content
    assert 'vest' in yaml_content
    assert 'gloves' in yaml_content

    # Check that we have train and val samples
    assert result['train_samples'] > 0
    assert result['val_samples'] > 0
    assert result['train_samples'] + result['val_samples'] == 10

    # Check that label files exist and have correct format
    train_labels = os.listdir(f'{tmp_path}/labels/train')
    assert len(train_labels) == result['train_samples']

    for label_file in train_labels:
        label_path = f'{tmp_path}/labels/train/{label_file}'
        assert os.path.exists(label_path)

        with open(label_path, 'r') as f:
            lines = f.readlines()

        # Each line should be: class_id x_center y_center width height
        for line in lines:
            parts = line.strip().split()
            assert len(parts) == 5  # 5 values per annotation

            class_id = int(parts[0])
            assert 0 <= class_id < 3  # Valid class index

            x_center = float(parts[1])
            y_center = float(parts[2])
            width = float(parts[3])
            height = float(parts[4])

            # All values should be normalized between 0 and 1
            assert 0.0 <= x_center <= 1.0
            assert 0.0 <= y_center <= 1.0
            assert 0.0 <= width <= 1.0
            assert 0.0 <= height <= 1.0


def test_export_project_not_found(db, tmp_path):
    """Test exporting non-existent project"""
    exporter = YOLOExporter()

    result = exporter.export_project(
        db=db,
        project_id=str(uuid.uuid4()),
        output_dir=str(tmp_path)
    )

    assert result['success'] is False
    assert 'error' in result


def test_export_no_annotations(db, test_user, tmp_path):
    """Test exporting project with no annotations"""
    from backend.training_db import TrainingProjectDB
    exporter = YOLOExporter()

    # Create project without annotations
    project_db = TrainingProjectDB()
    project = project_db.create_project(
        db=db,
        user_id=test_user,
        name="Empty Project",
        description="No annotations",
        target_classes=["helmet"]
    )

    result = exporter.export_project(
        db=db,
        project_id=project['id'],
        output_dir=str(tmp_path)
    )

    assert result['success'] is False
    assert 'No annotated frames found' in result['error']
