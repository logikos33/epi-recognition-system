"""
Pytest configuration and fixtures

Loads environment variables and provides common fixtures for tests.
"""
import pytest
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@pytest.fixture(scope="session")
def db_engine():
    """Create database engine for testing."""
    from backend.database import engine, init_db
    init_db()
    return engine
