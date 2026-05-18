from jose import jwt

from backend.app.core.config import settings
from backend.app.services.auth_service import create_access_token, decode_access_token


def test_create_access_token_contains_email_subject():
    token = create_access_token("user@example.com")

    payload = jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=[settings.jwt_algorithm],
    )

    assert payload["sub"] == "user@example.com"


def test_decode_access_token_returns_normalized_email():
    token = create_access_token("User@Example.com")

    assert decode_access_token(token) == "user@example.com"


def test_decode_access_token_returns_none_for_invalid_token():
    assert decode_access_token("not-a-valid-token") is None
