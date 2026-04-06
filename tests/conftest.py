"""
Pytest configuration and shared fixtures.

The top-level conftest intentionally does NOT connect to a real database so
that unit tests remain fast and hermetic.  Integration/e2e fixtures that
require a real database should live in their own conftest or be skipped when
DATABASE_URL is not set.
"""
import os
import pytest
from dotenv import load_dotenv

load_dotenv()


# ---------------------------------------------------------------------------
# Application factory fixtures (available to all test modules)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def app():
    """Create a Flask test application with no real database."""
    from backend.app import create_app
    application = create_app("testing")
    # Ensure tests never accidentally hit a production database
    application.config["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", "")
    return application


@pytest.fixture(scope="session")
def client(app):
    """Flask test client."""
    return app.test_client()


# ---------------------------------------------------------------------------
# Legacy integration fixture — skipped when DATABASE_URL is absent
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def db_engine():
    """
    SQLAlchemy engine for integration tests that require a real database.
    Tests using this fixture are skipped when TEST_DATABASE_URL is not set.
    """
    url = os.environ.get("TEST_DATABASE_URL", "")
    if not url:
        pytest.skip("TEST_DATABASE_URL not configured — skipping DB integration test")
    try:
        from backend.database import engine, init_db
        init_db()
        return engine
    except ImportError:
        pytest.skip("Legacy backend.database module not available")
