# tests/test_fueling_db.py
import pytest
from backend.database import get_db, engine
from sqlalchemy import text


def test_bays_table_exists():
    """Test that bays table was created"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'bays'
            )
        """))
        exists = result.scalar()
        assert exists is True, "bays table should exist"


def test_cameras_table_exists():
    """Test that cameras table was created"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'cameras'
            )
        """))
        exists = result.scalar()
        assert exists is True, "cameras table should exist"


def test_fueling_sessions_table_exists():
    """Test that fueling_sessions table was created"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'fueling_sessions'
            )
        """))
        exists = result.scalar()
        assert exists is True, "fueling_sessions table should exist"


def test_counted_products_table_exists():
    """Test that counted_products table was created"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'counted_products'
            )
        """))
        exists = result.scalar()
        assert exists is True, "counted_products table should exist"


def test_user_camera_layouts_table_exists():
    """Test that user_camera_layouts table was created"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'user_camera_layouts'
            )
        """))
        exists = result.scalar()
        assert exists is True, "user_camera_layouts table should exist"


def test_bays_table_structure():
    """Test that bays table has correct columns"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'bays'
            ORDER BY ordinal_position
        """))
        columns = {row[0]: {'type': row[1], 'nullable': row[2]} for row in result}

        assert 'id' in columns
        assert 'name' in columns
        assert 'location' in columns
        assert 'scale_integration' in columns
        assert 'created_at' in columns


def test_cameras_table_structure():
    """Test that cameras table has correct columns"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'cameras'
            ORDER BY ordinal_position
        """))
        columns = [row[0] for row in result]

        assert 'bay_id' in columns
        assert 'name' in columns
        assert 'rtsp_url' in columns
        assert 'is_active' in columns
        assert 'position_order' in columns