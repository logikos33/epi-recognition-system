"""Unit tests for JWT create_token / decode_token."""
import time
import pytest
import jwt as pyjwt

from backend.app.core.exceptions import AuthError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app():
    from backend.app import create_app
    application = create_app("testing")
    application.config["JWT_SECRET_KEY"] = "test-secret-key-for-unit-tests-only"
    application.config["JWT_TTL_SECONDS"] = 3600
    return application


@pytest.fixture
def app_ctx(app):
    with app.app_context():
        yield app


# ---------------------------------------------------------------------------
# create_token
# ---------------------------------------------------------------------------

class TestCreateToken:
    def test_returns_a_non_empty_string(self, app_ctx):
        from backend.app.core.auth import create_token
        token = create_token("user-123", "user@example.com")
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_has_three_jwt_segments(self, app_ctx):
        from backend.app.core.auth import create_token
        token = create_token("user-123", "user@example.com")
        assert token.count(".") == 2

    def test_token_contains_user_id_field(self, app_ctx):
        from backend.app.core.auth import create_token, decode_token
        token = create_token("user-abc", "a@b.com")
        payload = decode_token(token)
        assert payload["user_id"] == "user-abc"

    def test_token_contains_email_field(self, app_ctx):
        from backend.app.core.auth import create_token, decode_token
        token = create_token("user-abc", "a@b.com")
        payload = decode_token(token)
        assert payload["email"] == "a@b.com"

    def test_token_contains_exp_field(self, app_ctx):
        from backend.app.core.auth import create_token, decode_token
        token = create_token("user-abc", "a@b.com")
        payload = decode_token(token)
        assert "exp" in payload
        assert payload["exp"] > time.time()

    def test_custom_ttl_is_respected(self, app_ctx):
        from backend.app.core.auth import create_token
        before = int(time.time())
        token = create_token("u1", "x@y.com", ttl=7200)
        payload = pyjwt.decode(
            token,
            app_ctx.config["JWT_SECRET_KEY"],
            algorithms=["HS256"],
        )
        assert payload["exp"] >= before + 7200


# ---------------------------------------------------------------------------
# decode_token
# ---------------------------------------------------------------------------

class TestDecodeToken:
    def test_valid_token_returns_correct_payload(self, app_ctx):
        from backend.app.core.auth import create_token, decode_token
        token = create_token("user-xyz", "xyz@test.com")
        payload = decode_token(token)
        assert payload["user_id"] == "user-xyz"
        assert payload["email"] == "xyz@test.com"

    def test_expired_token_raises_auth_error(self, app_ctx):
        from backend.app.core.auth import decode_token
        # Manually craft an expired token
        payload = {
            "user_id": "u1",
            "email": "u1@test.com",
            "exp": int(time.time()) - 10,  # already expired
            "iat": int(time.time()) - 70,
        }
        expired_token = pyjwt.encode(
            payload,
            app_ctx.config["JWT_SECRET_KEY"],
            algorithm="HS256",
        )
        with pytest.raises(AuthError):
            decode_token(expired_token)

    def test_tampered_signature_raises_auth_error(self, app_ctx):
        from backend.app.core.auth import create_token, decode_token
        token = create_token("user-1", "u@test.com")
        # Flip the last character of the signature segment
        parts = token.split(".")
        parts[2] = parts[2][:-1] + ("A" if parts[2][-1] != "A" else "B")
        tampered = ".".join(parts)
        with pytest.raises(AuthError):
            decode_token(tampered)

    def test_token_signed_with_wrong_secret_raises_auth_error(self, app_ctx):
        from backend.app.core.auth import decode_token
        payload = {
            "user_id": "u1",
            "email": "u1@test.com",
            "exp": int(time.time()) + 3600,
        }
        bad_token = pyjwt.encode(payload, "wrong-secret", algorithm="HS256")
        with pytest.raises(AuthError):
            decode_token(bad_token)

    def test_garbage_string_raises_auth_error(self, app_ctx):
        from backend.app.core.auth import decode_token
        with pytest.raises(AuthError):
            decode_token("not.a.jwt")
