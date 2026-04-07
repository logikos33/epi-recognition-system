"""Unit tests for /api/v1/health/* endpoints (no real DB required)."""
import json
import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def app():
    from backend.app import create_app
    application = create_app("testing")
    # Ensure DB pool stays uninitialized so health/db returns 503
    application.config["DATABASE_URL"] = ""
    return application


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# /api/v1/health/ — top-level
# ---------------------------------------------------------------------------

class TestHealthRoot:
    def test_returns_200(self, client):
        response = client.get("/api/v1/health/")
        assert response.status_code == 200

    def test_body_has_status_ok(self, client):
        response = client.get("/api/v1/health/")
        body = json.loads(response.data)
        assert body["status"] == "ok"

    def test_body_contains_service_name(self, client):
        response = client.get("/api/v1/health/")
        body = json.loads(response.data)
        assert "service" in body

    def test_legacy_route_also_returns_200(self, client):
        # /api/v1/health (no trailing slash) is the legacy route
        response = client.get("/api/v1/health")
        assert response.status_code == 200


# ---------------------------------------------------------------------------
# /api/v1/health/db — database check
# ---------------------------------------------------------------------------

class TestHealthDb:
    def test_returns_503_when_db_pool_unavailable(self, client, mocker):
        # is_available checks _url (lazy pool — URL set but pool created on first use).
        # Patch _url to empty string so is_available returns False.
        from backend.app.infrastructure.database.connection import db_pool
        original = getattr(db_pool, "_url", None)
        db_pool._url = ""
        try:
            response = client.get("/api/v1/health/db")
            assert response.status_code == 503
        finally:
            db_pool._url = original

    def test_body_has_unavailable_status_when_db_pool_unavailable(self, client, mocker):
        from backend.app.infrastructure.database.connection import db_pool
        original = getattr(db_pool, "_url", None)
        db_pool._url = ""
        try:
            response = client.get("/api/v1/health/db")
            body = json.loads(response.data)
            assert body["status"] == "unavailable"
        finally:
            db_pool._url = original


# ---------------------------------------------------------------------------
# /api/v1/health/yolo — YOLO check
# ---------------------------------------------------------------------------

class TestHealthYolo:
    def test_returns_200_or_503(self, client):
        # Either outcome is acceptable — YOLO model may or may not be present
        response = client.get("/api/v1/health/yolo")
        assert response.status_code in (200, 503)

    def test_body_contains_service_yolo(self, client):
        response = client.get("/api/v1/health/yolo")
        body = json.loads(response.data)
        assert body.get("service") == "yolo"
