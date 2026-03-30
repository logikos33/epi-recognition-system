"""
Tests for YOLO Training Service.

This test suite validates the YOLOTrainer class which handles
YOLOv8 training execution and status tracking.
"""
import pytest
import uuid
from sqlalchemy import text
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
def test_project(db_session):
    """Create a test training project."""
    # First create a test user
    user_id = str(uuid.uuid4())
    user_query = text("""
        INSERT INTO users (id, email, password_hash, full_name, company_name, is_active, created_at)
        VALUES (:id, :email, :password_hash, :full_name, :company_name, true, NOW())
    """)

    db_session.execute(user_query, {
        'id': user_id,
        'email': f'test-trainer-{user_id[:8]}@example.com',
        'password_hash': 'dummy_hash',
        'full_name': 'Test User',
        'company_name': 'Test Company'
    })

    # Then create the project
    project_id = str(uuid.uuid4())

    query = text("""
        INSERT INTO training_projects
        (id, user_id, name, description, target_classes, status, created_at, updated_at)
        VALUES (:id, :user_id, :name, :description, CAST(:target_classes AS jsonb), 'draft', NOW(), NOW())
        RETURNING id
    """)

    db_session.execute(query, {
        'id': project_id,
        'user_id': user_id,
        'name': 'Test Project',
        'description': 'Test description',
        'target_classes': '["helmet", "vest"]'
    })
    db_session.commit()

    return project_id


def test_start_training_job(db_session, test_project, tmp_path):
    """Test starting a YOLO training job."""
    from backend.yolo_trainer import YOLOTrainer

    trainer = YOLOTrainer()

    config = {
        'epochs': 10,
        'batch_size': 8,
        'image_size': 640,
        'device': 'cpu'
    }

    result = trainer.start_training(
        db=db_session,
        project_id=test_project,
        config=config,
        augmentation={},
        model='yolov8n.pt'
    )

    assert result['success'] is True
    assert result['training_id'] is not None
    assert 'message' in result


def test_get_training_status(db_session, test_project):
    """Test getting training job status."""
    from backend.yolo_trainer import YOLOTrainer

    trainer = YOLOTrainer()

    # Start training first
    config = {'epochs': 10, 'batch_size': 8, 'device': 'cpu'}
    start_result = trainer.start_training(
        db=db_session,
        project_id=test_project,
        config=config,
        augmentation={},
        model='yolov8n.pt'
    )

    training_id = start_result['training_id']

    # Get status
    status = trainer.get_training_status(db_session, test_project)

    assert status['success'] is True
    assert 'status' in status
    assert status['status'] in ['queued', 'running', 'completed', 'failed']


def test_save_training_results(db_session, test_project):
    """Test saving training results to database."""
    from backend.yolo_trainer import YOLOTrainer

    trainer = YOLOTrainer()

    metrics = {
        'map50': 0.85,
        'map75': 0.75,
        'map50_95': 0.65,
        'precision': 0.88,
        'recall': 0.82
    }

    training_time_seconds = 300

    result = trainer.save_training_results(
        db=db_session,
        project_id=test_project,
        model_path='models/test_model.pt',
        metrics=metrics,
        training_time_seconds=training_time_seconds
    )

    assert result['success'] is True
    assert result['model_id'] is not None

    # Verify model was saved to database
    query = text("""
        SELECT id, model_name, storage_path, map50, precision, recall
        FROM trained_models
        WHERE id = :model_id
    """)
    row = db_session.execute(query, {'model_id': result['model_id']}).fetchone()

    assert row is not None
    assert str(row[0]) == result['model_id']
    assert float(row[3]) == 0.85


def test_get_active_model(db_session, test_project):
    """Test getting the active model for a project."""
    from backend.yolo_trainer import YOLOTrainer

    trainer = YOLOTrainer()

    # Initially no active model
    result = trainer.get_active_model(db_session, test_project)
    assert result['success'] is True
    assert result['model'] is None
