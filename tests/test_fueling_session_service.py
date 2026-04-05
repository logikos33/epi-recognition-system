# tests/test_fueling_session_service.py
import pytest
from backend.database import get_db, engine
from backend.fueling_session_service import FuelingSessionService
from sqlalchemy import text
import time
from datetime import datetime, timedelta


@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Cleanup test data before and after each test"""
    db = next(get_db())
    # Clean up any test sessions created during tests
    db.execute(text("""
        DELETE FROM counted_products
        WHERE session_id IN (
            SELECT id FROM fueling_sessions
            WHERE license_plate LIKE 'TEST-%'
        )
    """))
    db.execute(text("DELETE FROM fueling_sessions WHERE license_plate LIKE 'TEST-%'"))
    db.commit()
    yield
    # Cleanup after test
    db = next(get_db())
    db.execute(text("""
        DELETE FROM counted_products
        WHERE session_id IN (
            SELECT id FROM fueling_sessions
            WHERE license_plate LIKE 'TEST-%'
        )
    """))
    db.execute(text("DELETE FROM fueling_sessions WHERE license_plate LIKE 'TEST-%'"))
    db.commit()


def test_create_session():
    """Test creating a new fueling session"""
    db = next(get_db())

    # Get a bay_id and camera_id
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    result = db.execute(text("SELECT id FROM cameras LIMIT 1"))
    camera_id = result.scalar()

    # Create unique license plate
    timestamp = int(time.time())
    unique_plate = f"TEST-{timestamp}"

    session = FuelingSessionService.create_session(
        db=db,
        bay_id=bay_id,
        camera_id=camera_id,
        license_plate=unique_plate
    )

    assert session is not None
    assert session['license_plate'] == unique_plate
    assert session['bay_id'] == bay_id
    assert session['camera_id'] == camera_id
    assert session['status'] == 'active'
    assert session['truck_entry_time'] is not None
    assert 'id' in session


def test_get_session_by_id():
    """Test getting a specific session"""
    db = next(get_db())

    # Create a session first
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    result = db.execute(text("SELECT id FROM cameras LIMIT 1"))
    camera_id = result.scalar()

    timestamp = int(time.time())
    unique_plate = f"TEST-{timestamp}"

    created_session = FuelingSessionService.create_session(
        db=db,
        bay_id=bay_id,
        camera_id=camera_id,
        license_plate=unique_plate
    )

    # Get the session
    session = FuelingSessionService.get_session_by_id(db, created_session['id'])

    assert session is not None
    assert session['id'] == created_session['id']
    assert session['license_plate'] == unique_plate


def test_get_session_by_id_not_found():
    """Test getting a non-existent session"""
    db = next(get_db())

    session = FuelingSessionService.get_session_by_id(db, '00000000-0000-0000-0000-000000000000')

    assert session is None


def test_list_sessions():
    """Test listing all sessions"""
    db = next(get_db())

    # Create a test session
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    result = db.execute(text("SELECT id FROM cameras LIMIT 1"))
    camera_id = result.scalar()

    timestamp = int(time.time())
    unique_plate = f"TEST-{timestamp}"

    FuelingSessionService.create_session(
        db=db,
        bay_id=bay_id,
        camera_id=camera_id,
        license_plate=unique_plate
    )

    # List all sessions
    sessions = FuelingSessionService.list_sessions(db)

    assert isinstance(sessions, list)
    assert len(sessions) > 0
    # Should include our test session
    test_sessions = [s for s in sessions if s['license_plate'] == unique_plate]
    assert len(test_sessions) == 1


def test_list_sessions_with_filters():
    """Test listing sessions with bay_id and status filters"""
    db = next(get_db())

    # Get bay_id
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    result = db.execute(text("SELECT id FROM cameras LIMIT 1"))
    camera_id = result.scalar()

    timestamp = int(time.time())
    unique_plate = f"TEST-{timestamp}"

    # Create an active session
    FuelingSessionService.create_session(
        db=db,
        bay_id=bay_id,
        camera_id=camera_id,
        license_plate=unique_plate
    )

    # List sessions for specific bay
    sessions = FuelingSessionService.list_sessions(db, bay_id=bay_id)

    assert isinstance(sessions, list)
    # All returned sessions should be from this bay
    for session in sessions:
        assert session['bay_id'] == bay_id

    # List only active sessions
    active_sessions = FuelingSessionService.list_sessions(db, status='active')

    assert isinstance(active_sessions, list)
    # All returned sessions should be active
    for session in active_sessions:
        assert session['status'] == 'active'


def test_update_session():
    """Test updating session fields"""
    db = next(get_db())

    # Create a session
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    result = db.execute(text("SELECT id FROM cameras LIMIT 1"))
    camera_id = result.scalar()

    timestamp = int(time.time())
    unique_plate = f"T{timestamp % 10000}"  # Short plate to fit VARCHAR(20)

    created_session = FuelingSessionService.create_session(
        db=db,
        bay_id=bay_id,
        camera_id=camera_id,
        license_plate=unique_plate
    )

    # Update the session
    exit_time = datetime.now()
    updated_plate = f"U{timestamp % 10000}"  # Updated short plate
    updated_session = FuelingSessionService.update_session(
        db=db,
        session_id=created_session['id'],
        license_plate=updated_plate,
        truck_exit_time=exit_time,
        duration_seconds=300,
        final_weight=1500.5,
        status='completed'
    )

    assert updated_session is not None
    assert updated_session['license_plate'] == updated_plate
    assert updated_session['status'] == 'completed'
    assert updated_session['final_weight'] == 1500.5
    assert updated_session['duration_seconds'] == 300


def test_complete_session():
    """Test marking session as completed"""
    db = next(get_db())

    # Create a session
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    result = db.execute(text("SELECT id FROM cameras LIMIT 1"))
    camera_id = result.scalar()

    timestamp = int(time.time())
    unique_plate = f"TEST-{timestamp}"

    created_session = FuelingSessionService.create_session(
        db=db,
        bay_id=bay_id,
        camera_id=camera_id,
        license_plate=unique_plate
    )

    # Complete the session
    exit_time = datetime.now()
    completed_session = FuelingSessionService.complete_session(
        db=db,
        session_id=created_session['id'],
        truck_exit_time=exit_time
    )

    assert completed_session is not None
    assert completed_session['status'] == 'completed'
    assert completed_session['truck_exit_time'] is not None
    # Duration should be calculated
    assert completed_session['duration_seconds'] is not None
    assert completed_session['duration_seconds'] >= 0


def test_add_counted_product():
    """Test adding a counted product to a session"""
    db = next(get_db())

    # Create a session
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    result = db.execute(text("SELECT id FROM cameras LIMIT 1"))
    camera_id = result.scalar()

    timestamp = int(time.time())
    unique_plate = f"TEST-{timestamp}"

    session = FuelingSessionService.create_session(
        db=db,
        bay_id=bay_id,
        camera_id=camera_id,
        license_plate=unique_plate
    )

    # Add a counted product
    product = FuelingSessionService.add_counted_product(
        db=db,
        session_id=session['id'],
        product_type='Coca-Cola Lata',
        quantity=24,
        confidence=0.95,
        confirmed_by_user=True
    )

    assert product is not None
    assert product['product_type'] == 'Coca-Cola Lata'
    assert product['quantity'] == 24
    assert product['confidence'] == 0.95
    assert product['confirmed_by_user'] is True
    assert 'id' in product


def test_get_session_products():
    """Test getting all products for a session"""
    db = next(get_db())

    # Create a session
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    result = db.execute(text("SELECT id FROM cameras LIMIT 1"))
    camera_id = result.scalar()

    timestamp = int(time.time())
    unique_plate = f"TEST-{timestamp}"

    session = FuelingSessionService.create_session(
        db=db,
        bay_id=bay_id,
        camera_id=camera_id,
        license_plate=unique_plate
    )

    # Add multiple products
    FuelingSessionService.add_counted_product(
        db=db,
        session_id=session['id'],
        product_type='Coca-Cola Lata',
        quantity=24,
        confidence=0.95,
        confirmed_by_user=True
    )

    FuelingSessionService.add_counted_product(
        db=db,
        session_id=session['id'],
        product_type='Guaraná Antarctica',
        quantity=12,
        confidence=0.88,
        confirmed_by_user=False
    )

    # Get all products
    products = FuelingSessionService.get_session_products(db, session['id'])

    assert isinstance(products, list)
    assert len(products) == 2

    # Check first product
    assert products[0]['product_type'] == 'Coca-Cola Lata'
    assert products[0]['quantity'] == 24

    # Check second product
    assert products[1]['product_type'] == 'Guaraná Antarctica'
    assert products[1]['quantity'] == 12


def test_list_sessions_with_limit():
    """Test listing sessions with a limit"""
    db = next(get_db())

    # Get bay_id and camera_id
    result = db.execute(text("SELECT id FROM bays LIMIT 1"))
    bay_id = result.scalar()

    result = db.execute(text("SELECT id FROM cameras LIMIT 1"))
    camera_id = result.scalar()

    # Create multiple sessions
    for i in range(3):
        timestamp = int(time.time()) + i
        unique_plate = f"TEST-LIMIT-{timestamp}"
        FuelingSessionService.create_session(
            db=db,
            bay_id=bay_id,
            camera_id=camera_id,
            license_plate=unique_plate
        )

    # List with limit
    sessions = FuelingSessionService.list_sessions(db, limit=2)

    assert isinstance(sessions, list)
    assert len(sessions) <= 2
