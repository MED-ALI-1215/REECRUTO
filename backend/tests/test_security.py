import pytest
import time
from datetime import timedelta

from app.core.security import create_access_token, decode_access_token, generate_interview_token


class TestJWT:
    def test_encode_decode_roundtrip(self):
        token = create_access_token("admin")
        assert decode_access_token(token) == "admin"

    def test_expired_token_returns_none(self):
        # Create a token that expired 1 second ago
        token = create_access_token("admin", expires_delta=timedelta(seconds=-1))
        assert decode_access_token(token) is None

    def test_tampered_token_returns_none(self):
        token = create_access_token("admin")
        tampered = token[:-5] + "XXXXX"
        assert decode_access_token(tampered) is None

    def test_garbage_input_returns_none(self):
        assert decode_access_token("not.a.token") is None
        assert decode_access_token("") is None


class TestInterviewToken:
    def test_token_is_long_enough(self):
        token = generate_interview_token()
        assert len(token) >= 32

    def test_tokens_are_unique(self):
        tokens = {generate_interview_token() for _ in range(100)}
        assert len(tokens) == 100  # all unique
