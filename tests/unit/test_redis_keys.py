"""Tests for codex_platform.redis_service.keys."""

import pytest

from codex_platform.redis_service.keys import SessionKey, UserKey, resolve_key

pytestmark = pytest.mark.unit


class TestUserKey:
    def test_build(self):
        assert UserKey().build(user_id=42) == "u:42"

    def test_missing_arg_raises(self):
        with pytest.raises(ValueError, match="Missing key argument"):
            UserKey().build()

    def test_repr(self):
        assert repr(UserKey()) == "UserKey(template='u:{user_id}')"


class TestSessionKey:
    def test_build(self):
        assert SessionKey().build(token="abc") == "sess:abc"

    def test_missing_arg_raises(self):
        with pytest.raises(ValueError, match="Missing key argument"):
            SessionKey().build()

    def test_repr(self):
        assert repr(SessionKey()) == "SessionKey(template='sess:{token}')"


class TestResolveKey:
    def test_with_base_redis_key(self):
        assert resolve_key(UserKey(), user_id=42) == "u:42"

    def test_with_string(self):
        assert resolve_key("u:42") == "u:42"

    def test_with_string_ignores_kwargs(self):
        assert resolve_key("u:42", user_id=99) == "u:42"
