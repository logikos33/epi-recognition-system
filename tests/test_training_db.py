"""
Tests for training database operations.

This test suite validates the training_projects, training_videos,
training_frames, training_annotations, and trained_models tables.
"""
import pytest
import uuid
from sqlalchemy import text
from backend.database import get_db
from backend.training_db import TrainingProjectDB


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


def test_create_training_project(db, test_user):
    """Test creating a training project."""
    project_db = TrainingProjectDB()

    # Create test project
    project = project_db.create_project(
        db=db,
        user_id=test_user,
        name="Test Project",
        description="Test description",
        target_classes=["helmet", "vest"]
    )

    assert project is not None
    assert project['id'] is not None
    assert project['name'] == "Test Project"
    assert project['description'] == "Test description"
    assert project['target_classes'] == ["helmet", "vest"]
    assert project['status'] == "draft"


def test_get_training_project_by_id(db, test_user):
    """Test retrieving a training project by ID."""
    project_db = TrainingProjectDB()

    # Create project
    created = project_db.create_project(
        db=db,
        user_id=test_user,
        name="Get Test Project",
        description="Test retrieval",
        target_classes=["helmet"]
    )

    # Retrieve by ID
    retrieved = project_db.get_project(db, created['id'], test_user)

    assert retrieved is not None
    assert retrieved['id'] == created['id']
    assert retrieved['name'] == "Get Test Project"


def test_list_training_projects_by_user(db, test_user):
    """Test listing all training projects for a user."""
    project_db = TrainingProjectDB()

    # Create multiple projects
    project_db.create_project(
        db=db,
        user_id=test_user,
        name="Project 1",
        target_classes=["helmet"]
    )
    project_db.create_project(
        db=db,
        user_id=test_user,
        name="Project 2",
        target_classes=["vest"]
    )

    # List projects
    projects = project_db.list_user_projects(db, test_user)

    assert len(projects) >= 2
    project_names = [p['name'] for p in projects]
    assert "Project 1" in project_names
    assert "Project 2" in project_names


def test_update_training_project(db, test_user):
    """Test updating a training project."""
    project_db = TrainingProjectDB()

    # Create project
    created = project_db.create_project(
        db=db,
        user_id=test_user,
        name="Original Name",
        description="Original description",
        target_classes=["helmet"]
    )

    # Update project
    updated = project_db.update_project(
        db=db,
        project_id=created['id'],
        name="Updated Name",
        description="Updated description",
        target_classes=["helmet", "vest", "gloves"],
        status="in_progress"
    )

    assert updated['name'] == "Updated Name"
    assert updated['description'] == "Updated description"
    assert updated['target_classes'] == ["helmet", "vest", "gloves"]
    assert updated['status'] == "in_progress"


def test_delete_training_project(db, test_user):
    """Test deleting a training project."""
    project_db = TrainingProjectDB()

    # Create project
    created = project_db.create_project(
        db=db,
        user_id=test_user,
        name="To Delete",
        target_classes=["helmet"]
    )

    # Delete project
    result = project_db.delete_project(db, created['id'], test_user)
    assert result is True

    # Verify deletion
    retrieved = project_db.get_project(db, created['id'], test_user)
    assert retrieved is None


def test_training_project_tables_exist(db):
    """Test that all training tables exist in database."""
    tables_to_check = [
        'training_projects',
        'training_videos',
        'training_frames',
        'training_annotations',
        'trained_models'
    ]

    for table_name in tables_to_check:
        result = db.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = :table_name
            )
        """), {'table_name': table_name})

        exists = result.fetchone()[0]
        assert exists, f"Table {table_name} does not exist"


def test_training_projects_table_structure(db):
    """Test that training_projects table has correct columns."""
    result = db.execute(text("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns
        WHERE table_name = 'training_projects'
        ORDER BY ordinal_position
    """))

    columns = {row[0]: {'type': row[1], 'nullable': row[2]} for row in result.fetchall()}

    # Verify key columns exist
    assert 'id' in columns
    assert 'user_id' in columns
    assert 'name' in columns
    assert 'description' in columns
    assert 'target_classes' in columns
    assert 'status' in columns
    assert 'created_at' in columns
    assert 'updated_at' in columns

    # Verify data types
    assert columns['id']['type'] == 'uuid'
    assert columns['name']['type'] == 'character varying'
    assert columns['target_classes']['type'] == 'jsonb'


def test_update_project_status_only(db, test_user):
    """Test updating only the status of a training project."""
    project_db = TrainingProjectDB()

    # Create project
    created = project_db.create_project(
        db=db,
        user_id=test_user,
        name="Status Test Project",
        target_classes=["helmet"]
    )

    # Update status using the simplified method
    result = project_db.update_project_status(db, created['id'], 'in_progress')
    assert result is True

    # Verify status was updated
    retrieved = project_db.get_project(db, created['id'], test_user)
    assert retrieved['status'] == 'in_progress'

    # Test updating non-existent project
    fake_id = str(uuid.uuid4())
    result = project_db.update_project_status(db, fake_id, 'completed')
    assert result is False

    # Test retrieving with wrong user_id returns None
    wrong_user = str(uuid.uuid4())
    retrieved = project_db.get_project(db, created['id'], wrong_user)
    assert retrieved is None
