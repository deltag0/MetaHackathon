"""Unit tests — pure functions, no HTTP, no DB."""
import time

import pytest

from app.routes.links import _generate_short_code, _valid_url


# ---------------------------------------------------------------------------
# _valid_url
# ---------------------------------------------------------------------------

def test_valid_url_http():
    assert _valid_url("http://example.com") is True


def test_valid_url_https():
    assert _valid_url("https://example.com") is True


def test_valid_url_https_with_path():
    assert _valid_url("https://example.com/some/path?q=1") is True


def test_invalid_url_no_scheme():
    assert _valid_url("example.com") is False


def test_invalid_url_ftp():
    assert _valid_url("ftp://example.com") is False


def test_invalid_url_javascript():
    assert _valid_url("javascript:alert(1)") is False


def test_invalid_url_empty():
    assert _valid_url("") is False


def test_invalid_url_garbage():
    assert _valid_url("not a url at all") is False


def test_invalid_url_scheme_only():
    assert _valid_url("https://") is False


# ---------------------------------------------------------------------------
# _generate_short_code
# ---------------------------------------------------------------------------

def test_short_code_default_length():
    code = _generate_short_code()
    assert len(code) == 7


def test_short_code_custom_length():
    code = _generate_short_code(length=5)
    assert len(code) == 5


def test_short_code_alphanumeric():
    import re
    code = _generate_short_code()
    assert re.match(r"^[A-Za-z0-9]+$", code)


def test_short_code_unique():
    codes = {_generate_short_code() for _ in range(20)}
    # Extremely unlikely all 20 are the same
    assert len(codes) > 1


# ---------------------------------------------------------------------------
# session token helpers
# ---------------------------------------------------------------------------

def test_session_token_roundtrip(app):
    from app.routes.auth import _make_session_token, _verify_session_token
    with app.app_context():
        token = _make_session_token(42)
        assert _verify_session_token(token) == 42


def test_session_token_bad_signature(app):
    from app.routes.auth import _verify_session_token
    with app.app_context():
        assert _verify_session_token("this.is.not.valid") is None


def test_session_token_tampered(app):
    from app.routes.auth import _make_session_token, _verify_session_token
    with app.app_context():
        token = _make_session_token(1)
        tampered = token[:-4] + "xxxx"
        assert _verify_session_token(tampered) is None
