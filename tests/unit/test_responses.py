"""Unit tests for standardized response helpers."""
import json
import pytest


@pytest.fixture
def app():
    from backend.app import create_app
    return create_app("testing")


@pytest.fixture
def ctx(app):
    with app.app_context():
        yield app


# ---------------------------------------------------------------------------
# success()
# ---------------------------------------------------------------------------

class TestSuccessResponse:
    def test_returns_200_status_code(self, ctx):
        from backend.app.core.responses import success
        _, status = success()
        assert status == 200

    def test_body_has_success_true(self, ctx):
        from backend.app.core.responses import success
        resp, _ = success()
        body = json.loads(resp.data)
        assert body["success"] is True

    def test_body_includes_message(self, ctx):
        from backend.app.core.responses import success
        resp, _ = success(message="All good")
        body = json.loads(resp.data)
        assert body["message"] == "All good"

    def test_body_includes_data_when_provided(self, ctx):
        from backend.app.core.responses import success
        resp, _ = success(data={"id": 1})
        body = json.loads(resp.data)
        assert body["data"] == {"id": 1}

    def test_body_omits_data_key_when_not_provided(self, ctx):
        from backend.app.core.responses import success
        resp, _ = success()
        body = json.loads(resp.data)
        assert "data" not in body

    def test_custom_status_code_is_returned(self, ctx):
        from backend.app.core.responses import success
        _, status = success(status=202)
        assert status == 202


# ---------------------------------------------------------------------------
# created()
# ---------------------------------------------------------------------------

class TestCreatedResponse:
    def test_returns_201_status_code(self, ctx):
        from backend.app.core.responses import created
        _, status = created()
        assert status == 201

    def test_body_has_success_true(self, ctx):
        from backend.app.core.responses import created
        resp, _ = created()
        body = json.loads(resp.data)
        assert body["success"] is True


# ---------------------------------------------------------------------------
# error()
# ---------------------------------------------------------------------------

class TestErrorResponse:
    def test_returns_400_by_default(self, ctx):
        from backend.app.core.responses import error
        _, status = error("bad request")
        assert status == 400

    def test_body_has_success_false(self, ctx):
        from backend.app.core.responses import error
        resp, _ = error("oops")
        body = json.loads(resp.data)
        assert body["success"] is False

    def test_body_contains_error_message(self, ctx):
        from backend.app.core.responses import error
        resp, _ = error("something broke")
        body = json.loads(resp.data)
        assert body["error"] == "something broke"

    def test_custom_status_code_is_returned(self, ctx):
        from backend.app.core.responses import error
        _, status = error("conflict", status=409)
        assert status == 409

    def test_details_included_when_provided(self, ctx):
        from backend.app.core.responses import error
        resp, _ = error("validation failed", details={"field": "email"})
        body = json.loads(resp.data)
        assert body["details"] == {"field": "email"}

    def test_details_omitted_when_not_provided(self, ctx):
        from backend.app.core.responses import error
        resp, _ = error("bad")
        body = json.loads(resp.data)
        assert "details" not in body


# ---------------------------------------------------------------------------
# not_found()
# ---------------------------------------------------------------------------

class TestNotFoundResponse:
    def test_returns_404_status_code(self, ctx):
        from backend.app.core.responses import not_found
        _, status = not_found()
        assert status == 404

    def test_body_has_success_false(self, ctx):
        from backend.app.core.responses import not_found
        resp, _ = not_found()
        body = json.loads(resp.data)
        assert body["success"] is False

    def test_resource_name_appears_in_error_message(self, ctx):
        from backend.app.core.responses import not_found
        resp, _ = not_found("Camera")
        body = json.loads(resp.data)
        assert "Camera" in body["error"]


# ---------------------------------------------------------------------------
# unauthorized()
# ---------------------------------------------------------------------------

class TestUnauthorizedResponse:
    def test_returns_401_status_code(self, ctx):
        from backend.app.core.responses import unauthorized
        _, status = unauthorized()
        assert status == 401

    def test_body_has_success_false(self, ctx):
        from backend.app.core.responses import unauthorized
        resp, _ = unauthorized()
        body = json.loads(resp.data)
        assert body["success"] is False

    def test_custom_message_is_returned(self, ctx):
        from backend.app.core.responses import unauthorized
        resp, _ = unauthorized("Token expired")
        body = json.loads(resp.data)
        assert body["error"] == "Token expired"
